import { useOutletContext } from "react-router-dom";
import type { Register } from "../types";

/** What the risks layout hands the pages inside it. */
export type RisksOutlet = {
  register: Register;
  registers: Register[];
  selectRegister: (id: string) => void;
  addRisk: () => void;
  openImport: () => void;
  canManage: boolean;
  canConfigure: boolean;
};

export function useRisksOutlet(): RisksOutlet {
  return useOutletContext<RisksOutlet>();
}

const STORAGE_KEY = "verity.risks.register";

export function rememberedRegister(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function rememberRegister(id: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Storage can be unavailable (private mode); the default register still works.
  }
}
