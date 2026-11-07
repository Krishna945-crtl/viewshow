import { Suspense } from "react";
import Checkout from "./Checkout";

export default function Page() {
  return (
    <Suspense>
      <Checkout />
    </Suspense>
  );
}
