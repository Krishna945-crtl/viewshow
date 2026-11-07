import { Suspense } from "react";
import Showtimes from "./Showtimes";

export default function Page() {
  return (
    <Suspense>
      <Showtimes />
    </Suspense>
  );
}
