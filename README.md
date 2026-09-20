# mjartist.com — the new site

A fast, standalone website for Michael Joseph. It's plain HTML, CSS and JavaScript with no server, database or login page, so there's very little to hack. All the words and pictures live in three files in `content/`, and Michael edits them through a simple web app called **Pages CMS**. Every save goes live about a minute later.

```
index.html  work.html  about.html  exhibitions.html  contact.html   ← the pages
content/artworks.json      ← every artwork (title, series, photo, medium, size, price…)
content/exhibitions.json   ← shows (upcoming / on now / past is worked out automatically)
content/site.json          ← statement, biography, timeline, contact details
images/                    ← photos (uploads land here)
.pages.yml                 ← what the editing app shows
.github/workflows/         ← publishes the site, shrinks big photos, imports from Wix
tools/                     ← the scripts those workflows run
_headers                   ← security headers (used if you host on Cloudflare/Netlify)
```

---

## How the site is built
Every time something is saved, a small build script (`tools/build_site.py`) writes out every page as plain HTML, including **one page per artwork** (`art/tryst.html` and so on), plus the sitemap and search data. Then GitHub publishes it. You never run this yourself; `preview.bat` runs it for you on your computer.

**Don't edit the `.html` files by hand.** They're regenerated on every publish. Change the content in the editor, or the layout in `tools/build_site.py`, `assets/css/style.css` and `assets/js/site.js`.

The films are in `media/`. The looping clips (Bean Pod, the pour) have no sound. The full casting film keeps its soundtrack but starts muted; visitors can turn the sound on with the film's own controls. The loops only play while on screen, have a pause button, and show a still image to anyone whose device is set to reduce motion.

## 1. Preview it on your computer

Double-click **`preview.bat`** (Windows), or run `./preview.sh` on a Mac. Your browser opens at `http://localhost:8000`. It needs Python installed. Opening `index.html` directly won't work, because browsers block pages from reading the content files that way.

Until step 4 is done, the artwork photos load from Wix's servers.

## 2. Put it on GitHub

1. Make a GitHub account for the site, or use yours. **Turn on two-factor sign-in straight away** (Settings → Password and authentication; a passkey is best).
2. Create a new repository called `mjartist`. Private is fine.
3. Upload everything in this folder, including the hidden `.github` folder and `.pages.yml`. The easy way is GitHub Desktop: add the folder as a repository, then publish it.

## 3. Turn on hosting (GitHub Pages)

1. In the repo, go to **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Open the **Actions** tab. "Publish site" runs on every change. When it's green, the site is live at `https://<your-username>.github.io/mjartist/`.
3. **Custom domain:** go to Settings → Pages → Custom domain → `www.mjartist.com`. Then, wherever the domain's DNS is managed:
   - `CNAME` record: `www` → `<your-username>.github.io`
   - `A` records for the bare domain `mjartist.com`: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - When the certificate appears, tick **Enforce HTTPS**.
4. **Verify the domain** (this blocks anyone else from hijacking it on GitHub): your profile Settings → Pages → Add a domain → add the TXT record GitHub gives you.

> Private repos can only use GitHub Pages on a paid GitHub plan. With a free account, make the repo public. Nothing in it is secret: the contact-form key is designed to be public, and there are no passwords anywhere.

## 4. Copy the photos off Wix (do this before cancelling Wix)

Go to **Actions → Publish site → Run workflow**, tick **"Import images from Wix"**, and run it. It downloads all 130 originals and resizes them to web size. It then removes hidden camera data (like GPS location), saves them into `images/`, and updates the content files. After that the site no longer depends on Wix at all.

Afterwards you can tighten the security policy by removing `https://static.wixstatic.com` from the Content-Security-Policy line in the five `.html` files and in `_headers`.

## 5. Set up the editor for Michael

1. Michael makes his own free GitHub account, **with two-factor sign-in on**.
2. Repo → Settings → Collaborators → invite him (Write access). This gives him this one repository only.
3. Go to **app.pagescms.org** and sign in with GitHub. When it asks, install the Pages CMS app on **only the `mjartist` repository**, not "All repositories".
4. Michael bookmarks app.pagescms.org, signs in and picks `mjartist`. He'll see three sections:
   - **Artworks**: add a work, upload a photo (straight from a phone is fine; big photos shrink automatically), choose *What is it?* (Sculpture / Drawing / Painting / Mixed media) and the series, then fill in medium, size, price and availability. Other photos of the same piece go in *More photos*. A drawing or small model made on the way to a finished piece is marked *Study* or *Maquette* and linked to it (see `CHECK-WITH-MICHAEL.md` for the naming convention). Drag to reorder. Tick *Include in home page slideshow* for the 6–12 pieces that rotate beside his name, and *Show first on home page* to bring a work to the front of the Sculpture or Creative Figure row.
   - **Exhibitions**: add the venue and the open and close dates. The site shows *Upcoming*, *On now* or *Past* by itself.
   - **Course dates**: add a course with its date and booking link. Past courses drop off by themselves. Leave the date blank to show "coming soon".
   - **Courses & tuition**: the Courses page text, the ways to learn, student comments, the intro video and the Art Junction links.
   - **About, contact & home page**: statement, biography, timeline, the Sculpture and Creative Figure page text, the foundry steps, the scale feature, email, phone and Instagram. The home page story (*From line to bronze*) is also here; each chapter names an artwork, so its picture updates automatically.
5. Press **Save**. The site updates in about a minute.

Adding a new *series* means adding its name to the list under `series` in `.pages.yml`.

## Getting found on Google (do this once the site is live)
The site already does the technical part:
- A proper title and description on every page.
- A page for every artwork, with its image, medium and size.
- Structured data that tells Google this is an artist, with artworks, exhibitions and a course.
- A sitemap that includes every image.
- Share previews for WhatsApp, Facebook and LinkedIn.

What only you can do:
1. **Google Search Console** (search.google.com/search-console): add `mjartist.com` as a Domain property, verify it with the TXT record it gives you (added in Wix → Domains → DNS), then go to *Sitemaps* and submit `https://www.mjartist.com/sitemap.xml`.
2. **Bing Webmaster Tools:** sign in and choose "Import from Google Search Console". It takes two minutes.
3. **Ask for links:** Art Junction, Surrey Sculpture Society, Hannah Peschar, Oxmarket Gallery, the Guild of Aviation Artists and each exhibition venue.
4. **Keep filling in details:** medium, size, year and a sentence of notes on the key works. Search engines read those words.

## Fonts and licensing

All three typefaces are released under the SIL Open Font License, so they're free for commercial use and self-hosting forever. There's no fee, no account and nothing to expire. The licence files are in the fonts' original packages on Google Fonts.
- **Syne** (the big headings), by Bonjour Monde, commissioned for the Synesthésies art centre in Paris
- **Newsreader** (body text), by Production Type
- **IBM Plex Mono** (the small labels), by IBM

Free means anyone else can use them too. For something no one else has, the strongest option is to use **Michael's own signature** as the logo: photograph it on white paper and it can be traced into a crisp vector wordmark.

## 6. Contact form and spam (optional upgrade)

**Default:** the form opens the visitor's own email app with the message ready to send. No service is involved, so there is nothing for spammers to abuse.

**To have messages delivered straight to Michael's inbox:**
1. Get a free access key at **web3forms.com**, using Michael's email address.
2. Paste it into the editor: **About, contact & home page → Contact form key**.

**Spam protection, in layers (all free):**
1. **Two hidden "honeypot" fields** that people never see but bots fill in. Those messages are silently discarded, and the bot is shown a normal "thank you" so it doesn't try again.
2. **A time check.** A form completed in under 4 seconds is treated as a bot.
3. **Content checks.** Messages with HTML or link code, more than two web links, a missing message or an invalid email are stopped, with a plain explanation for real visitors.
4. **One message a minute** from the same browser.
5. **Web3Forms' own server-side spam filter** screens everything that reaches them.
6. **An optional "I am human" check (hCaptcha).** Tick **Contact form — add "I am human" check** in the editor if spam still gets through. It adds one small click for visitors, so it's off by default.

## 7. Instagram on the home page

The home page Instagram section always links to **@michael.joseph.artist**. There are two ways to show posts on the site as well:

**A. Latest posts, automatically (recommended)**
1. Sign up free at **behold.so** and connect Michael's Instagram account.
2. Create a feed, choose **JSON** as the type, and copy its address (it looks like `https://feeds.behold.so/AbC123`).
3. Paste it into the editor: **About, contact & home page → Instagram feed**.

The site then shows the latest 6–8 posts as a grid (captions appear on hover). It refreshes every morning, because GitHub rebuilds the site daily.

The pictures are copied onto the website when it's built, so visitors' browsers never contact Instagram and there's no Instagram tracking. Behold's free plan (1 feed, 6 posts, daily updates) is enough.

**B. Chosen posts, with no sign-up**

Paste individual post links (e.g. `https://www.instagram.com/p/DZXhu2TqPc1/`) into **Chosen Instagram posts**. They appear as Instagram's own embeds, with likes and captions. This loads Instagram's script for visitors, and the security policy allows exactly that and nothing wider.

If both are filled in, the automatic feed is used.

> On a **public** GitHub repository, GitHub pauses the daily rebuild after 60 days with no changes. Any edit restarts it, or you can switch it back on under the **Actions** tab.

## Security: what's built in, and the checklist

**Built into the site**
- There's no server, database, admin page or plugins on the website itself, so the common ways sites get hacked don't apply.
- A strict Content-Security-Policy is set in every page. Only the site's own files run, plus exactly three named services, each allowed only for its job: **Instagram** (post embeds, if you choose them), **Web3Forms/hCaptcha** (the contact form, if switched on) and **YouTube's privacy mode** (the Art Junction video, after a click). There are no trackers or analytics, and the fonts are self-hosted, which keeps UK GDPR simple.
- All text from the content files is inserted as plain text, never as HTML. Links are checked to be `https://` (or `mailto:`), and images must come from `images/` (or Wix during the changeover). A typo, or even a malicious edit, can't inject code.
- External links open with `rel="noopener noreferrer"`. The form has length limits and a spam honeypot.
- Uploaded photos have camera metadata (GPS location, device) removed automatically.
- The publishing workflow pins every GitHub Action to an exact commit and the Pillow library to an exact file hash, gives each step only the permissions it needs, and publishes only the public website files. The tools, workflows and settings are never served.
- `/.well-known/security.txt` tells anyone who finds a problem how to report it.
- The Art Junction introduction video is click-to-play. Nothing loads from YouTube (so no Google cookies) until a visitor presses play, and even then it plays in YouTube's privacy-enhanced mode inside a locked-down frame. The security policy allows only YouTube's privacy-enhanced player to be embedded, and only its thumbnail images.
- The automatic Instagram feed is fetched when the site is built and served from the site itself, so it adds no tracking. Only the optional chosen-post embeds load Instagram's own script.

**What you need to do (these accounts are where the real risk is)**
- [ ] Two-factor sign-in (passkey or authenticator app, not SMS) on **every** GitHub account with access
- [ ] Pages CMS app installed on the `mjartist` repo only
- [ ] Michael's account has Write access only. You stay the only Admin.
- [ ] Optional: Settings → Branches → protect `main` from deletion and force-push
- [ ] Domain verified in GitHub Pages settings (step 3.4)
- [ ] At the domain registrar: two-factor sign-in on, **transfer lock** on, auto-renew on, contact email current
- [ ] Remove the Wix entry from the security policy once images are imported (step 4)

**Where the domain lives.** If mjartist.com was bought through Wix, you can keep it there and just change the DNS records above. For fewer eggs in Wix's basket, transfer it to Cloudflare Registrar (at-cost pricing, free DNSSEC).

## Optional: host on Cloudflare instead

GitHub Pages is fine for a portfolio. Cloudflare adds full security headers (the `_headers` file: HSTS, anti-framing and the rest), DDoS shielding and free privacy-friendly visitor stats, but it's one more account to secure. In the Cloudflare dashboard → Workers & Pages → Create → import the same GitHub repo, with no build command and output directory `/`. The `.assetsignore` file keeps the tools and settings from being published. Pages CMS works exactly the same. Then turn off GitHub Pages.
