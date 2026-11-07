import { Suspense } from "react";
import ThemeLab from "./ThemeLab";

export default function Page() {
  return (
    <Suspense>
      <ThemeLab />
    </Suspense>
  );
}
