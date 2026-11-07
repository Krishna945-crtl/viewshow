import { Suspense } from "react";
import AuthForm from "@/components/ui/AuthForm";

export default function Page() {
  return (
    <Suspense>
      <AuthForm mode="login" />
    </Suspense>
  );
}
