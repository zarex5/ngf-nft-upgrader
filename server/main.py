import requests as req
import time
import datetime as dt
import traceback
from pymongo import MongoClient
import json
import base58
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.transaction import Transaction
from solana.account import Account

from util import wait, load_json_attributes
from arweave import send_to_arweave
from rpc import get_txs, get_tx, get_data_from_mint, is_tx_success, get_nfts
from metadata import get_metadata_py, update_metadata_instruction_data, update_metadata_instruction

WAIT_CYCLES = 40
WAIT_REQUEST = 1
WAIT_ERROR = 7

INO_IN_KINO = 1000
LAMPORT_IN_SOL = 0.000000001
MIN_AMOUNT_IN_SOL = 0.05

TO_PAY_ADDR = "AH3ypVQB6Bdje9m8DiqZ7kLQbtaW9fthCPCo4a355CN1"
SOLANA_CLIENT = Client("https://api.mainnet-beta.solana.com")
METADATA_PROGRAM_ID = PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s')
API_NGF_ENDPOINT = "https://token.nogoal.click:5050/ngf-img"
TEMP_FOLDER = "TEMP"

KEYPAIR = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # TODO: Change
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
ARWEAVE_PASSCODE = "secret"  # TODO: Change 
URL = "mongodb://username:password@localhost:27017"  # TODO: Change 
CLIENT = MongoClient(URL)
INO_DB = CLIENT["table"] # TODO: Change 


# SUB-PROCESS
def compute_current_layers(mint):
    data = get_data_from_mint(mint)
    attributes = data["attributes"]
    curr_layers = []
    _, _, _, attribute_key_to_layer = get_attributes_map()
    for attr in attributes:
        key = attr["trait_type"] + "#" + str(attr["value"])
        if key in attribute_key_to_layer:
            curr_layers.append(attribute_key_to_layer[key])
    return curr_layers


def compute_theo_ino_price(mint, layers):
    _, _, layer_to_ino_price, _ = get_attributes_map()
    curr_layers = compute_current_layers(mint)

    added = set(layers).difference(curr_layers)
    removed = set(curr_layers).difference(layers)

    additions_price = sum([layer_to_ino_price[layer] for layer in added])
    deletions_price = sum([layer_to_ino_price[layer]/float(2) for layer in removed])
    return additions_price - deletions_price


# PROCESS
def check_before_update(tx_res):
    if not is_tx_success(tx_res):
        raise Exception('Not a successful TX')

    if len(tx_res['result']['transaction']['message']['instructions']) != 4:
        raise Exception('Invalid TX format (not 4 instructions)')

    try:
        inolamports = int(tx_res['result']['transaction']['message']['instructions'][0]['parsed']['info']['amount'])
        lamports = tx_res['result']['transaction']['message']['instructions'][1]['parsed']['info']['lamports']
        mint = tx_res['result']['transaction']['message']['instructions'][2]['parsed']['info']['destination']
        data = tx_res['result']['transaction']['message']['instructions'][3]['parsed']['info']['destination']
    except KeyError:
        raise Exception('Invalid TX format (unable to retrieve sol, ino, mint or data)')

    sol = lamports * LAMPORT_IN_SOL
    if sol < MIN_AMOUNT_IN_SOL:
        raise Exception('Not enough SOL received (' + str(sol) + ' instead of at least ' + str(MIN_AMOUNT_IN_SOL) + ')')

    owned_nfts = get_nfts(payer)
    if mint not in owned_nfts:
        raise Exception('Payer does not own the NFT')

    data_str = base58.b58decode(data).decode("utf-8")
    data_str = data_str.replace("o", "0").replace("x", "")
    layers_str = data_str.split("E")
    layers = [int(num) for num in layers_str]
    if len(layers) != 11:
        raise Exception('Unable to decode the 11 layers (got ' + str(len(layers)) + ')')

    ino = inolamports * LAMPORT_IN_SOL
    theo_ino = compute_theo_ino_price(mint, layers)
    if ino < theo_ino:
        raise Exception('Not enough INO received (' + str(ino) + ' instead of at least ' + str(theo_ino) + ')')

    return [mint, layers, ino, sol]


def get_attributes_map():
    layer_to_json_attribute_map = {}
    layer_to_is_default_map = {}
    layer_to_ino_price = {}
    attribute_key_to_layer = {}

    attributes = load_json_attributes()
    for attribute in attributes:
        attr_type = attribute["type"]
        i = 0
        for value in attribute["values"]:
            layer_to_json_attribute_map[value["layer"]] = {"trait_type": attr_type, "value": value["value"]}
            layer_to_is_default_map[value["layer"]] = (i != 0)
            layer_to_ino_price[value["layer"]] = value["price"]*INO_IN_KINO
            attribute_key_to_layer[attr_type + "#" + value["value"]] = value["layer"]
            i += 1
    return layer_to_json_attribute_map, layer_to_is_default_map, layer_to_ino_price, attribute_key_to_layer


def update_arweave(mint, layers):
    data = get_data_from_mint(mint)

    # Generate new image and upload arweave
    new_image_url = API_NGF_ENDPOINT + "?layers=" + ",".join(map(str, layers))
    new_image_data = req.get(new_image_url).content
    new_image_path = TEMP_FOLDER + "/" + mint + ".png"
    with open(new_image_path, 'wb') as handler:
        handler.write(new_image_data)
    new_ar_img_url = send_to_arweave(new_image_path, ARWEAVE_PASSCODE)

    # Generate new attributes array
    upgrades_count = 1
    for ext_attr in data["attributes"]:
        if ext_attr["trait_type"] == "Upgrades":
            upgrades_count = int(ext_attr["value"]) + 1
    layer_to_json_attribute_map, layer_to_is_default_map, _, _ = get_attributes_map()
    attributes = [layer_to_json_attribute_map[layer] for layer in layers]
    attributes_count = sum([layer_to_is_default_map[layer] for layer in layers])
    attributes.append({'trait_type': 'Attributes', 'value': attributes_count})
    attributes.append({'trait_type': 'Generation', 'value': 1})
    attributes.append({'trait_type': 'Upgrades', 'value': upgrades_count})

    # Update json metadata, store and upload arweave
    data["image"] = new_ar_img_url + '?ext=png'
    data["properties"]["files"][0]["uri"] = new_ar_img_url + '?ext=png'
    data["attributes"] = attributes
    new_json_path = TEMP_FOLDER + "/" + mint + ".json"
    with open(new_json_path, 'w') as outfile:
        json.dump(data, outfile)
    new_ar_json_url = send_to_arweave(new_json_path, ARWEAVE_PASSCODE)
    # print(new_ar_json_url)

    return new_ar_json_url


def update_metaplex(mint, ar_link):
    account = Account(bytes(KEYPAIR))
    mint_account = PublicKey(mint)

    metadata = get_metadata_py(SOLANA_CLIENT, mint_account)
    update_metadata_data = update_metadata_instruction_data(
        metadata['data']['name'],
        metadata['data']['symbol'],
        ar_link,
        500,
        metadata['data']['creators'],
        metadata['data']['verified'],
        metadata['data']['share']
    )
    update_metadata_ix = update_metadata_instruction(
        update_metadata_data,
        account.public_key(),
        mint_account,
    )

    tx = Transaction()
    tx = tx.add(update_metadata_ix)
    tx_sig = SOLANA_CLIENT.send_transaction(tx, account)
    return tx_sig["result"]


if __name__ == '__main__':
    cycle = 0
    last_block_time = int(time.time())
    while True:
        wait(WAIT_CYCLES)
        MIN_BLOCKTIME = last_block_time
        print("= = = = = = CYCLE " + str(cycle) + " = = = = = = (min bt: " + str(MIN_BLOCKTIME) + ")")

        res_txs = get_txs(TO_PAY_ADDR)
        if 'error' in res_txs:
            print("[ERROR] While getting txs, waiting 8 sec then retrying: " + str(res_txs))
            time.sleep(WAIT_ERROR)
            res_txs = get_txs(TO_PAY_ADDR)
            if 'error' in res_txs:
                print("[ERROR] While getting txs again, skipping cycle: " + str(res_txs))
                continue
        # print(res_txs)
        last_block_time = res_txs["result"][0]['blockTime']
        for entry in res_txs["result"]:
            tx = entry['signature']
            blocktime = entry['blockTime']

            if blocktime <= MIN_BLOCKTIME:
                # print("[WARN] Stopped processing older txs as blocktime " + str(blocktime) + " <= " + str(MIN_BLOCKTIME))
                break

            tx_res = get_tx(tx)
            print("[DEBUG] Processing: " + str(tx))

            payer = tx_res['result']['transaction']['message']['accountKeys'][0]['pubkey']
            try:
                mint, layers, sol, ino = check_before_update(tx_res)
                tx_update = ""
                try:
                    ar_link = update_arweave(mint, layers)
                    tx_update = update_metaplex(mint, ar_link)
                    print("SUCCESS tx: " + str(tx_update))
                    process_status = "SUCCESS"
                    process_details = ""
                except Exception as e:
                    print(e)
                    print(traceback.format_exc())
                    process_status = "FAIL"
                    process_details = str(e)

                entry = {
                    "address": payer,
                    "amount_paid_ino": ino,
                    "amount_paid_sol": sol,
                    "tx_payment": tx,
                    "tx_delivery": tx_update,
                    "process_status": process_status,
                    "process_details": process_details,
                    "process_time": dt.datetime.today()
                }
                result = INO_DB.upgrades.insert_one(entry)
            except Exception as e:
                print("[ERROR] " + str(e))
                entry = {"tx_payment": tx, "address": payer, "reason": str(e), "process_time": dt.datetime.today()}
                print(entry)
                result = INO_DB.upgradesfail.insert_one(entry)
        cycle += 1
