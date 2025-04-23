from celery import Celery

from app.core.config import settings
from app.services.bittensor_substrate_service import AsyncSubstrateService
from app.services.chutes_service import ChutesService
from app.services.datura_service import DaturaService


class CeleryTask:
    """
    Celery application configured to run background sentiment analysis tasks.

    Contains task definitions for fetching tweets and calculating sentiment.
    """

    def __init__(self):
        self.celery = Celery(
            'app.worker',
            broker=settings.redis_url,
            backend=settings.redis_url,
        )

        self.datura_service = DaturaService()
        self.chutes_service = ChutesService()
        self.substrate_service = AsyncSubstrateService()

        self._register_tasks()

    def _register_tasks(self):
        @self.celery.task(name='analyze_and_stake')
        def analyze_and_stake(netuid: int, hotkey: str) -> float:
            """
            Celery task that performs sentiment analysis on tweets for a given subnet
            and returns a numeric sentiment score.

            Args:
                netuid (int): The subnet ID.

            Returns:
                float: The sentiment score (between -100 and 100).
            """
            import asyncio

            async def async_analyze_and_stake(netuid: int) -> float:
                try:
                    tweets = await self.datura_service.search_tweets(netuid)
                    sentiment = await self.chutes_service.get_sentiment_score(tweets)
                    await self.substrate_service.submit_stake_adjustment(netuid, hotkey, sentiment)
                    return sentiment

                except Exception as _:
                    return 0.0

            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(async_analyze_and_stake(netuid))
            return result


celery_app = CeleryTask().celery
analyze_and_stake = celery_app.tasks['analyze_and_stake']
