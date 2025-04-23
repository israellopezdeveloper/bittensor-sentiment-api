#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import bittensor as bt


def parse_arguments():
    """Parse command line arguments for wallet operations.

    Returns:
        argparse.Namespace: Parsed arguments with the following attributes:
            - name (str): Wallet name (required)
            - mnemonics (list): List of mnemonic words for wallet recovery
            - amount (float): Amount of TAO to transfer from faucet
    """
    parser = argparse.ArgumentParser(description='Bittensor Testnet Wallet Manager')
    parser.add_argument('--name', required=True, help='Name for the wallet')
    parser.add_argument('--mnemonics', nargs='+', help='Mnemonic words for wallet recovery')
    parser.add_argument('--amount', type=float, help='Amount of TAO to transfer from faucet')
    return parser.parse_args()


def setup_environment():
    """Configure the environment for testnet operations."""
    bt.subtensor.network = 'test'
    os.makedirs('./wallets', exist_ok=True)


def wallet_exists(wallet_name: str) -> bool:
    """Check if a wallet already exists in the wallets directory.

    Args:
        wallet_name (str): Name of the wallet to check

    Returns:
        bool: True if wallet exists, False otherwise
    """
    wallet_path = Path(f'./wallets/{wallet_name}')
    return wallet_path.exists()


def create_or_regenerate_wallet(
    wallet_name: str, mnemonics: Optional[list[str]] = None
) -> bt.wallet:
    """Create or regenerate a wallet on the testnet.

    Args:
        wallet_name (str): Name for the wallet
        mnemonics (list, optional): Mnemonic words for recovery

    Returns:
        bt.wallet: Initialized wallet instance

    Raises:
        SystemExit: If wallet operation fails
    """
    try:
        setup_environment()

        # Handle existing wallet
        if wallet_exists(wallet_name) and not mnemonics:
            print(f"\nℹ️ Wallet '{wallet_name}' already exists. Using existing wallet.")
            return bt.wallet(name=wallet_name, hotkey='default', path='./wallets')

        wallet = bt.wallet(name=wallet_name, hotkey='default', path='./wallets')

        if mnemonics:
            # Recover wallet from mnemonics
            mnemonic_phrase = ' '.join(mnemonics)
            print('\n🔑 Recovering wallet from mnemonics...')
            wallet.regenerate_coldkey(mnemonic=mnemonic_phrase, use_password=False, overwrite=True)
            wallet.create_new_hotkey(use_password=False)
        else:
            # Create new wallet only if it doesn't exist
            if not wallet_exists(wallet_name):
                wallet.create_new_coldkey(use_password=False)
                wallet.create_new_hotkey(use_password=False)
            else:
                return wallet

        print(
            f'\n✅ Wallet successfully {"recovered" if mnemonics else "created"} at ./wallets/{wallet_name}'
        )
        print(f'📌 Coldkey address: {wallet.coldkeypub.ss58_address}')
        print(f'📌 Hotkey address: {wallet.hotkey.ss58_address}')

        return wallet

    except Exception as e:
        print(f'❌ Failed to {"recover" if mnemonics else "create"} wallet: {str(e)}')
        sys.exit(1)


def transfer_from_faucet(wallet: bt.wallet, amount: float):
    """Transfer TAO from the faucet wallet to the specified wallet.

    Args:
        wallet (bt.wallet): Destination wallet
        amount (float): Amount of TAO to transfer

    Raises:
        SystemExit: If transfer fails
    """
    try:
        # Create temporary faucet wallet
        faucet_wallet = bt.wallet(
            name='faucet_temp', hotkey='default', path='./wallets/temp_faucet'
        )

        # Recover faucet wallet from hardcoded mnemonics
        faucet_wallet.regenerate_coldkey(
            mnemonic='diamond like interest affair safe clarify lawsuit innocent beef van grief color',
            use_password=False,
            overwrite=True,
        )

        # Execute transfer
        subtensor = bt.subtensor(network='test')
        print(f'\n🔄 Transferring {amount} TAO to {wallet.coldkeypub.ss58_address}...')

        subtensor.transfer(
            wallet=faucet_wallet,
            dest=wallet.coldkeypub.ss58_address,
            amount=bt.Balance.from_tao(amount),
            wait_for_inclusion=True,
            wait_for_finalization=True,
        )

        # Clean up temporary wallet
        if os.path.exists('./wallets/temp_faucet'):
            os.system('rm -rf ./wallets/temp_faucet')

    except Exception as e:
        print(f'❌ Transfer failed: {str(e)}')
        sys.exit(1)


def check_balance(wallet: bt.wallet):
    """Display the current balance of a wallet.

    Args:
        wallet (bt.wallet): Wallet to check balance for

    Returns:
        float: Current balance in TAO

    Raises:
        SystemExit: If balance check fails
    """
    try:
        subtensor = bt.subtensor(network='test')
        balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
        print(f'\n💰 Current balance: {balance} TAO')
        return balance
    except Exception as e:
        print(f'❌ Failed to check balance: {str(e)}')
        sys.exit(1)


def main():
    """Main entry point for the Bittensor wallet manager."""
    print('\n=== 🚀 Bittensor Testnet Wallet Manager ===')

    args = parse_arguments()

    try:
        # Create/recover/load wallet
        wallet = create_or_regenerate_wallet(args.name, args.mnemonics)

        # Transfer tokens if amount specified
        if args.amount:
            print(f'\n🪙 Requesting {args.amount} TAO from faucet...')
            transfer_from_faucet(wallet, args.amount)

        # Display final balance
        check_balance(wallet)

        print('\n🎉 Operation completed successfully!')
        print(f'📁 Wallet location: ./wallets/{args.name}')

    except Exception as e:
        print(f'\n❌ Error: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
