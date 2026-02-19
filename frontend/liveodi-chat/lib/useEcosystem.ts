"use client";
import { useState, useEffect } from "react";
import { gateway } from "./odi-gateway";

interface Store {
  id: string;
  name: string;
  type: string;
  palette: { primary: string; accent: string };
  products_count: number;
  status: string;
}

export function useEcosystem() {
  const [stores, setStores] = useState<Store[]>([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    gateway
      .getEcosystem()
      .then((data) => {
        setStores(data.stores || []);
        setTotalProducts(data.total_products || 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return { stores, totalProducts, loading, totalStores: stores.length };
}
