"use client";
import { createContext, useCallback, useContext, useState } from "react";
import { study } from "./client";
import type { Wallet } from "./types";

type Ctx = {
  wallet: Wallet;
  allocate: (campaignId: string, amount: number, source: string) => Promise<void>;
  allocateBatch: (items: { campaignId: string; amount: number }[], source: string) => Promise<void>;
  amountFor: (campaignId: string) => number;
  enabled: boolean;
};
const WalletCtx = createContext<Ctx | null>(null);

export function WalletProvider({ initial, enabled, children }: { initial: Wallet; enabled: boolean; children: React.ReactNode }) {
  const [wallet, setWallet] = useState(initial);
  const allocate = useCallback(async (campaignId: string, amount: number, source: string) => {
    setWallet(await study.allocate(campaignId, amount, source));
  }, []);
  const allocateBatch = useCallback(async (items: { campaignId: string; amount: number }[], source: string) => {
    setWallet(await study.allocateBatch(items.map((i) => ({ ...i, source }))));
  }, []);
  const amountFor = (id: string) => wallet.items.find((i) => i.campaign.id === id)?.amount ?? 0;
  return <WalletCtx.Provider value={{ wallet, allocate, allocateBatch, amountFor, enabled }}>{children}</WalletCtx.Provider>;
}

export function useWallet(): Ctx | null {
  return useContext(WalletCtx);
}
