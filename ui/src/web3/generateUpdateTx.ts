import { PublicKey, SystemProgram, Transaction, Connection } from "@solana/web3.js";
import { Token } from "@solana/spl-token";
// @ts-ignore
import bs58 from 'bs58';
import * as splToken from "@solana/spl-token";

const TO = new PublicKey("AH3ypVQB6Bdje9m8DiqZ7kLQbtaW9fthCPCo4a355CN1");
const TO_INO = new PublicKey("9LmMsY2ikLxqixSabymiCqRJaWXxgvcNAjC3HSuaBM8e");
const INO_MINT = new PublicKey("E1PvPRPQvZNivZbXRL61AEGr71npZQ5JGxh4aWX7q9QA");

const associatedTokenProgramId = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');
const tokenProgramId = new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");

const LAMPORTS_IN_SOL = 1000000000;
const INOS_IN_KINO = 1000;

export async function generateUpdateTx(nftMint: string, layers: number[], solFees: number, kinoFees: number, connection: Connection, signer: PublicKey) {
    if(layers.length > 11)
        return;
    let str = layers.join("E");
    str = str.replace(/0/g, "o");
    let currLength = str.length;
    for(let i=0; i<(32-currLength); i++)
        str += "x";
    console.log(str);
    const encoded = bs58.encode(Buffer.from(str, 'ascii'));

    let tx = await performTx(
        nftMint,
        encoded,
        solFees*LAMPORTS_IN_SOL,
        kinoFees*LAMPORTS_IN_SOL*INOS_IN_KINO,
        connection,
        signer
    )
    return tx;
}

async function performTx(nftMint: string, data: string, lamportsFees: number, inoFees: number, connection: Connection, signer: PublicKey) {
    let { blockhash } = await connection.getRecentBlockhash();
    const transaction = new Transaction({
        recentBlockhash: blockhash,
        feePayer: signer,
    });  

    var associatedAccountPublicKey = await Token.getAssociatedTokenAddress(
        associatedTokenProgramId,
        tokenProgramId,
        INO_MINT,
        signer,
    );
    const userAssociatedTokenAddress = await connection.getParsedTokenAccountsByOwner(
        signer,
        {mint: INO_MINT}
    )
    if(userAssociatedTokenAddress.value.length == 0) {
        throw new Error("Could not find a INO token account! Are you sure you own some NoGoalTokens?");
    }
    let ixIno = splToken.Token.createTransferInstruction(
        splToken.TOKEN_PROGRAM_ID,
        associatedAccountPublicKey,
        TO_INO,
        signer,
        [],
        inoFees
    );
    transaction.add(ixIno);
    let ix = SystemProgram.transfer({
        fromPubkey: signer,
        toPubkey: TO,
        lamports: lamportsFees, 
    })
    transaction.add(ix);
    let ixDataMint = SystemProgram.transfer({
        fromPubkey: signer,
        toPubkey: new PublicKey(nftMint),
        lamports: 0
    })
    transaction.add(ixDataMint);
    let ixDataInfo = SystemProgram.transfer({
        fromPubkey: signer,
        toPubkey: new PublicKey(data),
        lamports: 0
    })
    transaction.add(ixDataInfo);
    return transaction;
}