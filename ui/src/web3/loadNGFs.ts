import { PublicKey, Connection } from "@solana/web3.js";
// @ts-ignore
import * as BufferLayout from 'buffer-layout';
import fetch from 'cross-fetch';
import axios from "axios";
import { NGF_MINTS } from '../data/mint-list'

const CONNECTION = new Connection('https://api.mainnet-beta.solana.com');
const EXPLORER_API_URL = "https://explorer-api.mainnet-beta.solana.com/";

const ACCOUNT_DATA_LAYOUT = BufferLayout.struct([
    BufferLayout.u8('key'),
    BufferLayout.blob(32, 'updateAuthority'),
    BufferLayout.blob(32, 'mint'),
    BufferLayout.blob(32, 'name'),
    BufferLayout.blob(10, 'symbol'),
    BufferLayout.blob(200, 'uri'),
    BufferLayout.u16('sellferFeeBasisPoints'),
    BufferLayout.blob(32, 'address'),
    BufferLayout.blob(8, 'verified'),
    BufferLayout.u8('share'),
    BufferLayout.blob(8, 'primary_sale_happened'),
    BufferLayout.blob(8, 'is_mutable'),
])
const METAPLEX_PROGRAM_ID = 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s';
const PROGRAM_ID = new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");

export async function loadNGFs(ownerAddr: string) {
    let ownedNgfs = await getTokensFromOwner(ownerAddr);
    let data = []
    for(let i=0; i<ownedNgfs.length; i++){
        let ngfData = await getData(ownedNgfs[i]);
        data.push(ngfData);
    }
    return data;
}

async function getTokensFromOwner(ownerAddr: string) {
    let payload = {
        "method": "getTokenAccountsByOwner",
        "jsonrpc": "2.0",
        "params": [ownerAddr, {"programId": PROGRAM_ID.toBase58()}, {"commitment": "processed", "encoding": "jsonParsed"}],
        "id": "1"
    };
    let call = await axios({
        method: 'post',
        url: EXPLORER_API_URL,
        data: payload
    });

    let ownedNgfs: string[] = [];

    let tokens = call.data.result.value;
    tokens.forEach((elt: any) => {
        let parsed = elt.account.data.parsed;

        let mint = parsed.info.mint;
        let amount = parsed.info.tokenAmount.uiAmount;
        let decimals = parsed.info.tokenAmount.decimals;

        if(decimals == 0 && amount == 1) {
            if(NGF_MINTS.includes(mint)) {
                ownedNgfs.push(mint);
            }
        }
        
    });
    return ownedNgfs;
}

async function getData(mint: string) {
    let buffer = (await getMint(mint)) as Buffer;
    let data = ACCOUNT_DATA_LAYOUT.decode(Buffer.from(buffer));
    let url = encodeURI(data.uri.toString('utf-8').substring(12).substring(0,63));
    return fetch(url)
        .then((res: { json: () => any; }) => res.json())
        .then((res: { name: any; image: any; attributes: any; }) => {
            let name = res.name;
            let image = res.image;
            let attributes = res.attributes;
            return {name: name, image: image, attributes: attributes, mint: mint};
        });
}

async function getMint(mint: string) {
    const mintPubkey = new PublicKey(mint);
    const metaplexPubkey = new PublicKey(METAPLEX_PROGRAM_ID);

    const seeds = [
        Buffer.from('metadata'),
        metaplexPubkey.toBuffer(),
        mintPubkey.toBuffer()
    ];
    const [pda, nonce] = await PublicKey.findProgramAddress(
        seeds,
        metaplexPubkey
    );
    
    const accountInfo = await CONNECTION.getAccountInfo(pda);
    if (accountInfo) {
        const data = accountInfo.data;
        return data;
    }
}