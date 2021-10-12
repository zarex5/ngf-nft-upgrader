import requests as req
import time
import base64
from solana.rpc.api import Client
from solana.publickey import PublicKey

SOLANA_CLIENT = Client("https://api.mainnet-beta.solana.com")
WAIT_REQUEST = 1


def get_tokens(addr):
    time.sleep(WAIT_REQUEST)
    headers = {'Content-Type': 'application/json'}
    data = '{"method":"getTokenAccountsByOwner","jsonrpc":"2.0","params":["' + f"{addr}" + '",{"programId":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},{"encoding":"jsonParsed","commitment":"processed"}], "id": 1}'
    response = req.post("https://api.mainnet-beta.solana.com", headers=headers, data=data)
    return response.json()


def get_txs(addr, nb_max=100):
    time.sleep(WAIT_REQUEST)
    headers = { 'Content-Type': 'application/json' }
    data = ' { "jsonrpc": "2.0", "id": 1, "method": "getConfirmedSignaturesForAddress2", "params": [ "' + f"{addr}" + '", { "limit": ' + str(nb_max) + ' } ] } '
    response = req.post("https://api.mainnet-beta.solana.com", headers=headers, data=data)
    return response.json()


def get_tx(tx):
    time.sleep(WAIT_REQUEST)
    headers = { 'Content-Type': 'application/json' }
    data = '{"method": "getConfirmedTransaction", "jsonrpc": "2.0", "params": ["' + f"{tx}" + '", {"encoding": "jsonParsed"}], "id": 1}'
    response = req.post("https://api.mainnet-beta.solana.com", headers=headers, data=data)
    return response.json()


def get_metadata(mint):
    metaplex_pubkey = PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
    mint_pubkey = PublicKey(mint)
    expected_token_account_key, _ = PublicKey.find_program_address(
        seeds=[str.encode('metadata'), bytes(metaplex_pubkey), bytes(mint_pubkey)],
        program_id=metaplex_pubkey,
    )
    info = SOLANA_CLIENT.get_account_info(expected_token_account_key)
    base64_content = info["result"]["value"]["data"][0]
    content = base64.b64decode(base64_content)[119:199].decode('utf-8')
    return content.replace('\x00', '')


# FUNCTIONS RELATED FROM RPC_CALLS
def get_data_from_mint(mint):
    metadata_url = get_metadata(mint)
    data = req.get(metadata_url).json()
    # print(data)
    return data


def is_tx_success(tx_res):
    try:
        return tx_res['result']['meta']['status']['Ok'] is None
    except KeyError:
        return False


def get_nfts(addr):
    mints = []
    res = get_tokens(addr)
    try:
        tokens = res['result']['value']
    except KeyError:
        print("[WARN] Unable to get getNfts result content (request failed), returning None")
        return []
    for token in tokens:
        decimals = token['account']['data']['parsed']['info']['tokenAmount']['decimals']
        amount = token['account']['data']['parsed']['info']['tokenAmount']['uiAmount']
        if amount == 1 and decimals == 0:
            mint = token['account']['data']['parsed']['info']['mint']
            mints.append(mint)
    return mints
