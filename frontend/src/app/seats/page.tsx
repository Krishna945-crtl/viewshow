import { Suspense } from "react";
import SeatSelection from "./SeatSelection";

export default function Page() {
  return (
    <Suspense>
      <SeatSelection />
    </Suspense>
  );
}
