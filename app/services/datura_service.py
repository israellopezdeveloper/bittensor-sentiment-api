from datetime import datetime, timezone

import httpx
from httpx import HTTPStatusError, RequestError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.core.config import settings


class DaturaService:
    """
    Service for retrieving recent tweets from the Datura API.

    Used to gather context for sentiment analysis related to Bittensor subnets.
    """

    API_URL = 'https://apis.datura.ai/twitter'

    @staticmethod
    @retry(
        stop=stop_after_attempt(settings.blockchain_max_retries),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((RequestError, HTTPStatusError)),
        reraise=True,
    )
    async def search_tweets(netuid: int) -> list[str]:
        """
        Search for recent tweets related to a specific netuid using Datura API.

        Args:
            netuid (int): The subnet ID to include in the tweet query.

        Returns:
            list[str]: A list of tweet texts.
        """
        end_date = datetime.now(timezone.utc).date()

        params = {
            'query': 'netuid:{}'.format(netuid),
            'blue_verified': False,
            'end_date': str(end_date),
            'is_image': False,
            'is_quote': False,
            'is_video': False,
            'lang': 'en',
            'min_likes': 0,
            'min_replies': 0,
            'min_retweets': 0,
            'sort': 'Top',
            'count': 10,
        }

        headers = {
            'Authorization': settings.datura_api_key,
            'Content-Type': 'application/json',
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(DaturaService.API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return [tweet['text'] for tweet in data if 'text' in tweet]
