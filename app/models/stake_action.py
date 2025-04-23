from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class StakeAction(SQLModel, table=True):
    """
    SQLModel table representing a record of a stake or unstake operation.

    Attributes:
        id (int | None): Primary key.
        timestamp (datetime): When the action was recorded.
        netuid (int): The subnet ID.
        hotkey (str): The wallet hotkey used in the transaction.
        sentiment (float): Sentiment score that triggered the action.
        stake_type (str): 'stake' or 'unstake'.
        tao_amount (float): TAO amount involved in the action.
        status (str): Status of the operation ('success' or 'error').
        error_message (str | None): Error message if operation failed.
    """

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    netuid: int
    hotkey: str
    sentiment: float
    stake_type: str
    tao_amount: float
    status: str
    error_message: str | None = None
