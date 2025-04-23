import re

import httpx
from httpx import RequestError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.core.config import settings


class ChutesService:
    """
    Service for analyzing sentiment from tweet content using the Chutes LLM API.

    Includes methods to build prompts, send requests to the model, extract sentiment scores,
    and handle failure gracefully with retries and fallback behavior.
    """

    BASE_URL = 'https://llm.chutes.ai/v1/chat/completions'

    @staticmethod
    def extract_sentiment_score(response: str) -> float:
        """
        Extract a numeric sentiment score from a string.

        Args:
            response (str): The response string returned by the LLM.

        Returns:
            float: A number between -100 and 100. Returns 0.0 if no valid number is found.
        """
        normalized = response.replace(',', '.')
        match = re.search(r'(-?\d+\.?\d*)', normalized)
        if match:
            try:
                result = float(match.group(1))
                if result < -100:
                    result = -100.0
                elif result > 100:
                    result = 100.0
                return result
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    @retry(
        stop=stop_after_attempt(settings.blockchain_max_retries),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((RequestError, KeyError, TypeError)),
        reraise=True,
    )
    async def _call_chutes(payload: dict, headers: dict) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ChutesService.BASE_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            isinstance(response.json()['choices'][0]['message']['content'], str)
            return response.json()

    @staticmethod
    async def get_sentiment_score(tweets: list[str]) -> float:
        """
        Evaluate the overall sentiment score of a list of tweets using Chutes API.

        Args:
            tweets (list[str]): A list of tweet texts.

        Returns:
            float: Sentiment score between -100 and 100.
        """
        if len(tweets) == 0:
            return 0.0
        prompt = (
            "I'll pass you several Bittensor-related tweets. Return a number "
            + 'between -100 and 100 that represents the overall sentiment. Where'
            + ' -100 is very negative, 0 is indifferent or unrelated, and 100'
            + ' is very positive. The response should only contain that number.'
            + '\n\n'
            + '\n'.join(tweets)
        )

        payload = {
            'model': 'unsloth/Llama-3.2-3B-Instruct',
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False,
            'max_tokens': 1024,
            'temperature': 0.7,
        }

        headers = {
            'Authorization': f'Bearer {settings.chutes_api_key}',
            'Content-Type': 'application/json',
        }

        try:
            data = await ChutesService._call_chutes(payload, headers)
            return ChutesService.extract_sentiment_score(
                data['choices'][0]['message']['content'],
            )
        except Exception as e:
            print(f'[ERROR] {e}', flush=True)
            return 0.0
