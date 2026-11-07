import { Suspense } from "react";
import MovieDetail from "./MovieDetail";

export default function Page() {
  return (
    <Suspense>
      <MovieDetail />
    </Suspense>
  );
}
