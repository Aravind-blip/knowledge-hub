import { redirect } from "next/navigation";
import { getServerAuth } from "@/lib/supabase/server";


export default async function HomePage() {
  const { user, authConfigured } = await getServerAuth();
  redirect(authConfigured ? (user ? "/documents" : "/login") : "/documents");
}
