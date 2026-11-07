import { Suspense } from "react";
import Ticket from "./Ticket";

export default function Page() {
  return (
    <Suspense>
      <Ticket />
    </Suspense>
  );
}
