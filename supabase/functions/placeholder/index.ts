// Placeholder Edge Function — scaffold for future async operations.
// Will be replaced by actual functions as modules M5+ are built.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

serve((_req: Request) => {
  return new Response(JSON.stringify({ status: "ok", message: "Widby Edge Functions scaffold" }), {
    headers: { "Content-Type": "application/json" },
  });
});
