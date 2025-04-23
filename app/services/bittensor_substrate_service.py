import asyncio
import binascii

from async_substrate_interface import AsyncQueryMapResult
from async_substrate_interface.async_substrate import AsyncSubstrateInterface
from bittensor import Balance, Wallet
from bittensor.core.async_subtensor import AsyncSubtensor
from bittensor.core.settings import SS58_FORMAT
from scalecodec import ss58_encode
from scalecodec.utils.ss58 import ss58_decode

from app.core.config import settings
from app.db.session import async_session
from app.models.stake_action import StakeAction


class AsyncSubstrateService:
    """
    Service for interacting with the Bittensor blockchain via the Subtensor substrate interface.

    Provides methods for:
    - Retrieving dividend data (per hotkey, per netuid, or all).
    - Submitting stake or unstake operations based on sentiment analysis.
    - Storing stake actions in the database.
    """

    def __init__(self, url: str = settings.blockchain_url):
        self.url = url
        self.substrate: AsyncSubstrateInterface = AsyncSubstrateInterface(
            url=self.url,
            ss58_format=SS58_FORMAT,
        )
        self.wallet: Wallet = Wallet(
            name=settings.test_wallet_name,
            hotkey=settings.test_wallet_name,
            path='./wallets',
        )
        self.wallet = self.wallet.create_if_non_existent()
        if not self.wallet.coldkeypub_file.exists_on_device():
            self.wallet.create_new_coldkey(use_password=False)
        if not self.wallet.hotkey_file.exists_on_device():
            self.wallet.create_new_hotkey(use_password=False)
        self.subtensor = AsyncSubtensor(network='test')

    async def _record_stake_action(
        self,
        netuid: int,
        hotkey: str,
        sentiment: float,
        stake_type: str,
        tao_amount: float,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """
        Store a record of the stake or unstake operation in the database.
        """
        try:
            async with async_session() as session:
                action = StakeAction(
                    netuid=netuid,
                    hotkey=hotkey,
                    sentiment=sentiment,
                    stake_type=stake_type,
                    tao_amount=tao_amount,
                    status=status,
                    error_message=error_message,
                )
                session.add(action)
                await session.commit()
        except Exception as e:
            print(f'[DB ERROR] Unable to save stake action: {e}', flush=True)

    @staticmethod
    async def exhaust(qmr):
        """
        Exhaust an async query map result into a list of tuples.
        """
        r = []
        async for k, v in qmr:
            r.append((k, v))
        return r

    @staticmethod
    def _parse_dividend_value(value) -> float | None:
        """
        Parse the dividend value ensuring it's numeric. Returns None otherwise.
        """
        if isinstance(value, (int, float)):
            return float(value)
        return None

    async def get_all_dividends(self) -> list:
        """
        Retrieve dividend data for all hotkeys across all subnets.
        """
        try:
            if not self.substrate:
                raise Exception('Substrate not connected')
            qmr: AsyncQueryMapResult = await self.substrate.query_map(
                module='SubtensorModule',
                storage_function='TaoDividendsPerSubnet',
            )
            results = []
            async for k, v in qmr:
                try:
                    netuid: int = k[0]
                    raw_hotkey = bytes(k[1][0])
                    hotkey: str = ss58_encode(raw_hotkey)
                    dividend = self._parse_dividend_value(v.value)

                    if dividend is None:
                        continue
                    results = self._add_dividends_to_all(results, netuid, hotkey, dividend)
                except Exception as e:
                    print(f'[WARN] Error decoding key {k}: {e}', flush=True)
                    continue

            return results
        except Exception as e:
            print(f'[ERROR] get_all_dividends failed: {e}', flush=True)
            return []

    async def get_dividends_for_netuid_hotkey(self, netuid: int, hotkey: str) -> float | None:
        """
        Fetch the current TAO dividend for a given netuid and hotkey.
        """
        try:
            if not self.substrate:
                raise Exception('Substrate not connected')
            block_hash = await self.substrate.get_chain_head()

            hotkey_bytes = binascii.unhexlify(ss58_decode(hotkey, valid_ss58_format=SS58_FORMAT))

            result = await self.substrate.query(
                module='SubtensorModule',
                storage_function='TaoDividendsPerSubnet',
                params=[netuid, hotkey_bytes],
                block_hash=block_hash,
            )

            return float(result.value) if result else None

        except Exception as e:
            print(f'[ERROR] Failed to fetch dividend: {e}', flush=True)
            return None

    async def get_dividends_for_netuid(self, netuid: int) -> list:
        """
        Retrieve dividend data for all hotkeys under a specific netuid.
        """
        try:
            if not self.substrate:
                raise Exception('Substrate not connected')
            qmr = await self.substrate.query_map(
                module='SubtensorModule',
                storage_function='TaoDividendsPerSubnet',
                params=[netuid],
            )

            result = []
            async for x in qmr:
                hotkey = ss58_encode(bytes(x[0][0]))
                result.append({
                    'hotkey': hotkey,
                    'dividend': x[1].value,
                })

            return result
        except Exception as e:
            print(f'[ERROR] get_dividends_for_netuid failed: {e}', flush=True)
            return []

    @staticmethod
    def _add_dividends_to_all(
        data: list[dict], netuid_to_verify: int, hotkey_to_add: str, dividends_to_add: float
    ) -> list[dict]:
        """
        Accumulate dividends grouped by netuid and hotkey.
        """
        for entry in data:
            if entry.get('netuid') == netuid_to_verify:
                entry['hotkeys'].append({'hotkey': hotkey_to_add, 'dividends': dividends_to_add})
                return data

        data.append({
            'netuid': netuid_to_verify,
            'hotkeys': [{'hotkey': hotkey_to_add, 'dividends': dividends_to_add}],
        })
        return data

    async def submit_stake_adjustment(self, netuid: int, hotkey: str, sentiment: float):
        """Handle stake adjustments with automatic hotkey registration if needed"""
        if sentiment == 0.0:
            return False

        try:
            if not self.wallet:
                raise Exception('Wallet not connected')

            # Convert amount to proper Balance with explicit netuid context
            stake_amount_tao = 0.01 * abs(sentiment)
            stake_amount = Balance.from_tao(stake_amount_tao)

            # Get balances with proper units
            coldkey_balance = await self.subtensor.get_balance(self.wallet.coldkeypub.ss58_address)
            current_stake = await self.subtensor.get_stake(
                coldkey_ss58=self.wallet.coldkeypub.ss58_address, hotkey_ss58=hotkey, netuid=netuid
            )

            print(f'Current coldkey balance: {coldkey_balance}')
            print(f'Current stake for {hotkey}: {current_stake}')
            print(f'Attempting to {"stake" if sentiment > 0 else "unstake"} {stake_amount}')

            # Check and handle hotkey registration with retries
            max_registration_attempts = 3
            is_registered = await self.subtensor.is_hotkey_registered(
                netuid=netuid, hotkey_ss58=hotkey
            )

            if not is_registered and sentiment > 0:  # Only register for stake operations
                print(
                    f'Hotkey {hotkey} not registered on subnet {netuid} - attempting registration...'
                )

                for attempt in range(max_registration_attempts):
                    try:
                        registration_result = await self.subtensor.register(
                            wallet=self.wallet,
                            netuid=netuid,
                            wait_for_inclusion=True,
                            wait_for_finalization=True,
                        )

                        if registration_result:
                            print(f'✅ Successfully registered hotkey (attempt {attempt + 1})')
                            is_registered = True
                            break
                        else:
                            print(f'⚠️ Registration attempt {attempt + 1} failed')

                    except Exception as e:
                        print(f'⚠️ Registration attempt {attempt + 1} error: {str(e)}')

                    if attempt < max_registration_attempts - 1:
                        await asyncio.sleep(5)  # Wait before retry

            if not is_registered:
                error_msg = (
                    'Hotkey not registered'
                    if sentiment > 0
                    else 'Cannot unstake - hotkey not registered'
                )
                print(error_msg)
                await self._record_stake_action(
                    netuid=netuid,
                    hotkey=hotkey,
                    sentiment=sentiment,
                    stake_type='stake' if sentiment > 0 else 'unstake',
                    tao_amount=float(stake_amount_tao),
                    status='failed',
                    error_message=error_msg,
                )
                return False

            # Proceed with stake/unstake operation
            if sentiment > 0:  # Stake operation
                if coldkey_balance < stake_amount:
                    print(f'Insufficient balance: {coldkey_balance} < {stake_amount}')
                    await self._record_stake_action(
                        netuid=netuid,
                        hotkey=hotkey,
                        sentiment=sentiment,
                        stake_type='stake',
                        tao_amount=stake_amount_tao,
                        status='failed',
                        error_message='Insufficient balance',
                    )
                    return False

                result = await self.subtensor.add_stake(
                    wallet=self.wallet,
                    netuid=netuid,
                    hotkey_ss58=hotkey,
                    amount=stake_amount,
                    wait_for_inclusion=True,
                    wait_for_finalization=True,
                )
            else:  # Unstake operation
                if current_stake < stake_amount:
                    print(f'Insufficient stake: {current_stake} < {stake_amount}')
                    await self._record_stake_action(
                        netuid=netuid,
                        hotkey=hotkey,
                        sentiment=sentiment,
                        stake_type='unstake',
                        tao_amount=float(stake_amount_tao),
                        status='failed',
                        error_message='Insufficient stake',
                    )
                    return False

                result = await self.subtensor.unstake(
                    wallet=self.wallet,
                    hotkey_ss58=hotkey,
                    netuid=netuid,
                    amount=stake_amount,
                    wait_for_inclusion=True,
                    wait_for_finalization=True,
                )

            if result:
                print(f'Successfully {"staked" if sentiment > 0 else "unstaked"} {stake_amount}')
                await self._record_stake_action(
                    netuid=netuid,
                    hotkey=hotkey,
                    sentiment=sentiment,
                    stake_type='stake' if sentiment > 0 else 'unstake',
                    tao_amount=float(stake_amount_tao),
                    status='success',
                )
                return True
            else:
                print('Transaction failed')
                await self._record_stake_action(
                    netuid=netuid,
                    hotkey=hotkey,
                    sentiment=sentiment,
                    stake_type='stake' if sentiment > 0 else 'unstake',
                    tao_amount=float(stake_amount_tao),
                    status='failed',
                    error_message='Transaction failed',
                )
                return False

        except Exception as e:
            error_msg = str(e)
            print(f'Error in stake adjustment: {error_msg}')
            await self._record_stake_action(
                netuid=netuid,
                hotkey=hotkey,
                sentiment=sentiment,
                stake_type='stake' if sentiment > 0 else 'unstake',
                tao_amount=float(stake_amount_tao),
                status='error',
                error_message=error_msg,
            )
            return False
