import base58
import base64
import struct
from construct import Bytes, Int8ul
from construct import Struct as cStruct  # type: ignore
from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction

METADATA_PROGRAM_ID = PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s')


def _get_data_buffer(name, symbol, uri, bips, creators, verified=None, share=None):
    if isinstance(share, list):
        assert(len(share) == len(creators))
    if isinstance(verified, list):
        assert(len(verified) == len(creators))
    args = [
        len(name),
        *list(name.encode()),
        len(symbol),
        *list(symbol.encode()),
        len(uri),
        *list(uri.encode()),
        bips,
    ]
    byte_fmt = "<"
    byte_fmt += "I" + "B"*len(name)
    byte_fmt += "I" + "B"*len(symbol)
    byte_fmt += "I" + "B"*len(uri)
    byte_fmt += "h"
    byte_fmt += "B"
    if creators:
        args.append(1)
        byte_fmt += "I"
        args.append(len(creators))
        for i, creator in enumerate(creators):
            byte_fmt +=  "B"*32 + "B" + "B"
            args.extend(list(base58.b58decode(creator)))
            if isinstance(verified, list):
                args.append(verified[i])
            else:
                args.append(1)
            if isinstance(share, list):
                args.append(share[i])
            else:
                args.append(100)
    else:
        args.append(0)
    buffer = struct.pack(byte_fmt, *args)
    return buffer


def unpack_metadata_account(data):
    assert(data[0] == 4)
    i = 1
    source_account = base58.b58encode(bytes(struct.unpack('<' + "B"*32, data[i:i+32])))
    i += 32
    mint_account = base58.b58encode(bytes(struct.unpack('<' + "B"*32, data[i:i+32])))
    i += 32
    name_len = struct.unpack('<I', data[i:i+4])[0]
    i += 4
    name = struct.unpack('<' + "B"*name_len, data[i:i+name_len])
    i += name_len
    symbol_len = struct.unpack('<I', data[i:i+4])[0]
    i += 4
    symbol = struct.unpack('<' + "B"*symbol_len, data[i:i+symbol_len])
    i += symbol_len
    uri_len = struct.unpack('<I', data[i:i+4])[0]
    i += 4
    uri = struct.unpack('<' + "B"*uri_len, data[i:i+uri_len])
    i += uri_len
    fee = struct.unpack('<h', data[i:i+2])[0]
    i += 2
    has_creator = data[i]
    i += 1
    if has_creator:
        creator_len = struct.unpack('<I', data[i:i+4])[0]
        i += 4
        creators = []
        verified = []
        share = []
        for _ in range(creator_len):
            creator = base58.b58encode(bytes(struct.unpack('<' + "B"*32, data[i:i+32])))
            creators.append(creator)
            i += 32
            verified.append(data[i])
            i += 1
            share.append(data[i])
            i += 1
    primary_sale_happened = bool(data[i])
    i += 1
    is_mutable = bool(data[i])
    metadata = {
        "update_authority": source_account,
        "mint": mint_account,
        "data": {
            "name": bytes(name).decode("utf-8"),
            "symbol": bytes(symbol).decode("utf-8"),
            "uri": bytes(uri).decode("utf-8"),
            "seller_fee_basis_points": fee,
            "creators": creators,
            "verified": verified,
            "share": share,
        },
        "primary_sale_happened": primary_sale_happened,
        "is_mutable": is_mutable,
    }
    return metadata


def update_metadata_instruction_data(name, symbol, uri, bips, creators, verified, share):
    _data = bytes([1]) + _get_data_buffer(name, symbol, uri, bips, creators, verified, share) + bytes([0, 0])
    instruction_layout = cStruct(
        "instruction_type" / Int8ul,
        "args" / Bytes(len(_data)),
    )
    return instruction_layout.build(
        dict(
            instruction_type=1,
            args=_data,
        )
    )


def get_metadata_py(client, mint_key):
    metadata_account = PublicKey.find_program_address(
        [b'metadata', bytes(METADATA_PROGRAM_ID), bytes(PublicKey(mint_key))],
        METADATA_PROGRAM_ID
    )[0]
    data = base64.b64decode(client.get_account_info(metadata_account, commitment='recent')['result']['value']['data'][0])
    metadata = unpack_metadata_account(data)
    return metadata


def update_metadata_instruction(data, update_authority, mint_key):
    metadata_account = PublicKey.find_program_address(
        [b'metadata', bytes(METADATA_PROGRAM_ID), bytes(PublicKey(mint_key))],
        METADATA_PROGRAM_ID
    )[0]
    keys = [
        AccountMeta(pubkey=metadata_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=update_authority, is_signer=True, is_writable=False),
    ]
    return TransactionInstruction(keys=keys, program_id=METADATA_PROGRAM_ID, data=data)
