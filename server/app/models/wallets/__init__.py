"""
Wallets domain — customer virtual balance, ledger, and rewards.

Import order: Wallet → WalletTransaction → UserReward
(Wallet is the root; transactions and rewards are children.)

NOTE: Vendor balances are handled by VendorWallet in the vendors domain.
"""

from app.models.wallets.wallet import Wallet, WalletStatus
from app.models.wallets.transaction import WalletTransaction, WalletTransactionStatus
from app.models.wallets.reward import UserReward, UserRewardStatus

__all__ = [
    # Models
    "Wallet",
    "WalletTransaction",
    "UserReward",
    # Local enums (move to enums.py in next enums update)
    "WalletStatus",
    "WalletTransactionStatus",
    "UserRewardStatus",
]
