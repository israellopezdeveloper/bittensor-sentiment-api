import os
from pathlib import Path
from typing import List, Optional

import bittensor as bt
from bittensor.utils.balance import Balance
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
WALLETS_DIR = './wallets'
FAUCET_MNEMONIC = 'diamond like interest affair safe clarify lawsuit innocent beef van grief color'


class WalletRequest(BaseModel):
    name: str = Field(default='testnet')
    mnemonics: Optional[List[str]] = None


class TransferRequest(BaseModel):
    name: str = Field(default='testnet')
    amount: float


def setup_environment():
    bt.subtensor.network = 'test'
    os.makedirs(WALLETS_DIR, exist_ok=True)


def wallet_exists(wallet_name: str) -> bool:
    return Path(f'{WALLETS_DIR}/{wallet_name}').exists()


def get_wallet(wallet_name: str, mnemonics: Optional[List[str]] = None) -> bt.wallet:
    setup_environment()
    wallet = bt.wallet(name=wallet_name, hotkey='default', path=WALLETS_DIR)

    if wallet_exists(wallet_name):
        return wallet

    if mnemonics:
        mnemonic_phrase = ' '.join(mnemonics)
        wallet.regenerate_coldkey(mnemonic=mnemonic_phrase, use_password=False, overwrite=True)
        wallet.create_new_hotkey(use_password=False)
    else:
        wallet.create_new_coldkey(use_password=False)
        wallet.create_new_hotkey(use_password=False)

    return wallet


def restore_faucet_wallet() -> bt.wallet:
    wallet = bt.wallet(name='faucet_temp', hotkey='default', path='./wallets/temp_faucet')
    wallet.regenerate_coldkey(mnemonic=FAUCET_MNEMONIC, use_password=False, overwrite=True)
    if not wallet.hotkey_file.exists_on_device:
        wallet.create_new_hotkey(use_password=False)
    return wallet


def check_balance(wallet: bt.wallet) -> float:
    subtensor = bt.subtensor(network='test')
    return float(subtensor.get_balance(wallet.coldkeypub.ss58_address))


@router.post('/create_wallet', tags=['Wallets'])
def create_wallet(data: WalletRequest):
    try:
        wallet = get_wallet(data.name, data.mnemonics)
        balance = check_balance(wallet)
        return {
            'wallet_name': data.name,
            'coldkey_address': wallet.coldkeypub.ss58_address,
            'hotkey_address': wallet.hotkey.ss58_address,
            'balance': balance,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post('/transfer', tags=['Wallets'])
def transfer(data: TransferRequest):
    if data.amount > 40.0:
        raise HTTPException(status_code=400, detail='Transfer amount cannot exceed 40.0 TAO')

    if not wallet_exists(data.name):
        raise HTTPException(status_code=404, detail=f"Wallet '{data.name}' does not exist")

    try:
        dest_wallet = bt.wallet(name=data.name, hotkey='default', path=WALLETS_DIR)
        faucet_wallet = restore_faucet_wallet()
        subtensor = bt.subtensor(network='test')

        subtensor.transfer(
            wallet=faucet_wallet,
            dest=dest_wallet.coldkeypub.ss58_address,
            amount=Balance.from_tao(data.amount),
            wait_for_inclusion=True,
            wait_for_finalization=True,
        )

        balance = check_balance(dest_wallet)
        return {
            'wallet_name': data.name,
            'coldkey_address': dest_wallet.coldkeypub.ss58_address,
            'balance': balance,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
