import re

with open("aegis-frontend/lib/api.ts", "r") as f:
    content = f.read()

fetch_retry_code = """
/**
 * Helper to fetch with exponential backoff for Render free tier cold starts.
 * It also catches HTML responses to prevent SyntaxError on res.json().
 */
async function fetchWithRetry(url: string, opts?: RequestInit): Promise<Response> {
  let retries = 5;
  let res;
  
  while (retries > 0) {
    res = await fetch(url, opts);
    if (res.ok) return res;
    
    if (res.status === 502 || res.status === 504) {
      retries--;
      if (retries === 0) throw new Error("Backend took too long to wake up. Please try again.");
      console.log(`Backend is waking up... retrying in 10s. (${retries} retries left)`);
      await new Promise(r => setTimeout(r, 10000));
      continue;
    }
    
    const text = await res.text().catch(() => "");
    try {
      const err = JSON.parse(text);
      throw new Error(err.detail || err.error || "Request failed");
    } catch (e) {
      throw new Error(text.slice(0, 100) || "Request failed");
    }
  }
  throw new Error("Request failed");
}
"""

if "fetchWithRetry" not in content:
    content = content.replace("export const api = {", fetch_retry_code + "\nexport const api = {")

# Replace exchangeGitHubCode
new_exchange = """  async exchangeGitHubCode(code: string) {
    const redirectUri = `${window.location.origin}/auth/callback`;
    const res = await fetchWithRetry(`${API_V1}/auth/github`, getOpts({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    }));
    const user = await res.json() as UserInfo;
    if (typeof window !== "undefined" && user?.id) {
      localStorage.setItem("aegis_user_id", String(user.id));
      localStorage.setItem("aegis_username", user.github_username);
      localStorage.setItem("aegis_avatar", user.github_avatar_url);
    }
    return user;
  },"""

# Replace the old exchangeGitHubCode using regex
content = re.sub(r"async exchangeGitHubCode\(code: string\) \{.*?return user;\n  \},", new_exchange, content, flags=re.DOTALL)


# Replace other fetch calls
content = re.sub(
    r"const res = await fetch\(([^)]+)\);\n\s*if \(!res\.ok\) \{\n\s*const err = await res\.json\(\);\n\s*throw new Error\(err\.detail \|\| \"([^\"]+)\"\);\n\s*\}\n\s*return res\.json\(\);",
    r"const res = await fetchWithRetry(\1);\n    return res.json();",
    content
)

# A more generic replace for standard fetch calls
content = re.sub(
    r"const res = await fetch\(([^,]+), ([^)]+)\);\n\s*if \(!res\.ok\) \{\n\s*const err = await res\.json\(\);\n\s*throw new Error\(err\.detail \|\| \"([^\"]+)\"\);\n\s*\}\n\s*return res\.json\(\);",
    r"const res = await fetchWithRetry(\1, \2);\n    return res.json();",
    content
)

content = re.sub(
    r"const res = await fetch\(([^)]+)\);\n\s*if \(!res\.ok\) throw new Error\(\"([^\"]+)\"\);\n\s*return res\.json\(\)( as Promise<[^>]+>)?;",
    r"const res = await fetchWithRetry(\1);\n    return res.json()\3;",
    content
)

# For methods with catch block in json parse
content = re.sub(
    r"const res = await fetch\(([^,]+), ([^)]+)\);\n\s*if \(!res\.ok\) \{\n\s*const err = await res\.json\(\)\.catch\(\(\) => \(\{.*?\}\)\);\n\s*throw new Error\(err\.(?:detail|error) \|\| \"([^\"]+)\"\);\n\s*\}\n\s*return res\.json\(\);",
    r"const res = await fetchWithRetry(\1, \2);\n    return res.json();",
    content, flags=re.DOTALL
)

# Simple replaces
content = content.replace("await fetch(`${API_V1}", "await fetchWithRetry(`${API_V1}")
# But wait, we shouldn't replace it in connectLiveFeed (EventSource)
# We already replaced all fetch calls. Let's just do a blanket replace for fetch( -> fetchWithRetry( inside api methods.
# Actually, the regex above handles most cases.

with open("aegis-frontend/lib/api.ts", "w") as f:
    f.write(content)
