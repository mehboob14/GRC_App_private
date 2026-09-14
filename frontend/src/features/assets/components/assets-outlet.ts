import type { MutableRefObject } from "react";
import { useOutletContext } from "react-router-dom";
import type { AssetFilters } from "../types";

/** The page of the register on screen: exactly what `listAssets` was called with. */
export type RegisterView = { filters: AssetFilters; page: number; pageSize: number };

/** What the assets layout hands the pages inside it. */
export type AssetsOutlet = {
  addAsset: () => void;
  /** The register keeps this current so Export in the header downloads the same
   *  page, filters included. Null when the register is not open. */
  registerView: MutableRefObject<RegisterView | null>;
};

export function useAssetsOutlet(): AssetsOutlet {
  return useOutletContext<AssetsOutlet>();
}
