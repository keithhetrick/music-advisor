export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname;
    async function getAppToken() {
      const creds = btoa(
        `${env.SPOTIFY_CLIENT_ID}:${env.SPOTIFY_CLIENT_SECRET}`
      );
      const r = await fetch("https://accounts.spotify.com/api/token", {
        method: "POST",
        headers: {
          Authorization: `Basic ${creds}`,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: "grant_type=client_credentials",
      });
      if (!r.ok) return new Response("Auth failed", { status: 500 });
      return (await r.json()).access_token;
    }
    function tonalName(key, mode) {
      const KEYS = [
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "A#",
        "B",
      ];
      if (key == null || key < 0) return null;
      const root = KEYS[key % 12];
      return mode === 1 ? `${root} major` : `${root} minor`;
    }
    const token = await getAppToken();

    if (path === "/searchTrack") {
      const q = url.searchParams.get("q");
      if (!q)
        return new Response(JSON.stringify({ error: "Missing q" }), {
          status: 400,
        });
      const r = await fetch(
        `https://api.spotify.com/v1/search?type=track&limit=1&q=${encodeURIComponent(
          q
        )}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await r.json();
      if (!data.tracks?.items?.length)
        return new Response(JSON.stringify({ found: false }), {
          headers: { "Content-Type": "application/json" },
        });
      const t = data.tracks.items[0];
      return new Response(
        JSON.stringify({
          found: true,
          id: t.id,
          name: t.name,
          artists: t.artists.map((a) => a.name),
          duration_ms: t.duration_ms,
          popularity: t.popularity,
          url: t.external_urls?.spotify || null,
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }
    if (path === "/audioFeatures") {
      const id = url.searchParams.get("id");
      if (!id)
        return new Response(JSON.stringify({ error: "Missing id" }), {
          status: 400,
        });
      const r = await fetch(`https://api.spotify.com/v1/audio-features/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const f = await r.json();
      return new Response(
        JSON.stringify({
          ok: !f.error,
          tempo: f.tempo ?? null,
          key: f.key ?? null,
          mode: f.mode ?? null,
          tonal_center: tonalName(f.key, f.mode),
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }
    return new Response(
      JSON.stringify({
        ok: true,
        info: "/searchTrack?q=ARTIST - TRACK, /audioFeatures?id=ID",
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  },
};
