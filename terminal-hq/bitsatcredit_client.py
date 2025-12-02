#!/usr/bin/env python3
"""
BitSatCredit Extension API Client
Handles all credit operations via the LNbits BitSatCredit extension
"""

import requests
from typing import Optional, Dict, Any


class BitSatCreditClient:
    def __init__(self, extension_url: str):
        """
        Initialize BitSatCredit extension client

        Args:
            extension_url: Base URL of BitSatCredit extension (e.g., "https://lnbits.example.com/bitsatcredit")
        """
        self.extension_url = extension_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

    def get_user(self, npub: str) -> Optional[Dict[str, Any]]:
        """
        Get user account (read-only, does not create new users)

        Args:
            npub: User's nostr public key (npub format)

        Returns:
            User data dict or None if user doesn't exist or on error
        """
        try:
            # Use balance endpoint which doesn't auto-create users
            response = self.session.get(f"{self.extension_url}/api/v1/user/{npub}/balance")
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # User doesn't exist - they need to top up first
                return None
            print(f"Error getting user {npub[:16]}...: {e}")
            return None
        except Exception as e:
            print(f"Error getting user {npub[:16]}...: {e}")
            return None

    def get_balance(self, npub: str) -> Optional[Dict[str, Any]]:
        """
        Get user's current balance

        Args:
            npub: User's nostr public key

        Returns:
            Balance data dict with keys: npub, balance_sats, total_spent, total_deposited, message_count
        """
        try:
            response = self.session.get(f"{self.extension_url}/api/v1/user/{npub}/balance")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting balance for {npub[:16]}...: {e}")
            return None

    def can_spend(self, npub: str, amount: int) -> bool:
        """
        Check if user has sufficient balance to spend amount

        Args:
            npub: User's nostr public key
            amount: Amount in sats to check

        Returns:
            True if user can afford amount, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.extension_url}/api/v1/user/{npub}/can-spend",
                params={'amount': amount}
            )
            response.raise_for_status()
            data = response.json()
            return data.get('can_afford', False)
        except Exception as e:
            print(f"Error checking spend for {npub[:16]}...: {e}")
            return False

    def spend_credits(self, npub: str, amount: int, memo: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Deduct credits from user balance (called when message is sent)

        Args:
            npub: User's nostr public key
            amount: Amount in sats to deduct
            memo: Optional memo for transaction

        Returns:
            Updated user data or None on error
        """
        try:
            params = {'amount': amount}
            if memo:
                params['memo'] = memo

            response = self.session.post(
                f"{self.extension_url}/api/v1/user/{npub}/spend",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 402:
                print(f"Insufficient balance for {npub[:16]}...")
            elif e.response.status_code == 404:
                print(f"User not found: {npub[:16]}...")
            else:
                print(f"Error spending credits for {npub[:16]}...: {e}")
            return None
        except Exception as e:
            print(f"Error spending credits for {npub[:16]}...: {e}")
            return None

    def get_transactions(self, npub: str) -> list:
        """
        Get user's transaction history

        Args:
            npub: User's nostr public key

        Returns:
            List of transaction dicts
        """
        try:
            response = self.session.get(f"{self.extension_url}/api/v1/user/{npub}/transactions")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting transactions for {npub[:16]}...: {e}")
            return []

    def create_invoice(self, npub: str, amount: int) -> Optional[Dict[str, Any]]:
        """
        Create a Lightning invoice for user to top up credits

        Args:
            npub: User's nostr public key
            amount: Amount in sats to invoice

        Returns:
            Invoice data dict with keys: payment_request, payment_hash, or None on error
        """
        try:
            response = self.session.post(
                f"{self.extension_url}/api/v1/user/{npub}/invoice",
                params={'amount': amount}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating invoice for {npub[:16]}...: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check if extension API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.session.get(f"{self.extension_url}/api/v1/health")
            response.raise_for_status()
            data = response.json()
            return data.get('status') == 'ok'
        except Exception as e:
            print(f"Extension health check failed: {e}")
            return False
