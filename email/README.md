# Email

## halloween/

Halloween "free week of LORD" email, rebuilt from the approved design (`halloween/reference-v1.webp`).

- `index.html` is the email: table layout with inline styles, 600px wide, stacks on phones. Text, buttons and links are live HTML, so copy edits happen here.
- `img/` holds placeholder images **cropped from the 600px reference screenshot**. They're 1x and soft on retina screens. Replace them with the original source art (hero, drip band, LORD badge, social icons) before sending.
- The hero image has the logo and the "Halloween update" pill baked in.
- Merge tags (`{{ first_name }}`, `{% unsubscribe %}`, `{% manage_preferences %}`) use Klaviyo syntax.
- Links marked `REPLACE_ME` (YouTube, TikTok, Twitter) still need real URLs. The Store and Website URLs are guesses, so check them too.

Preview locally:

    /opt/pw-browsers/chromium-1194/chrome-linux/chrome --headless --no-sandbox --hide-scrollbars \
      --window-size=640,1700 --screenshot=preview.png file://$PWD/halloween/index.html

## halloween/v2 and creator/ (exact copies)

Exact copies of the approved designs (`reference.webp` in each folder). `plate.png` is the screenshot with only the text erased, so all the art, buttons, icons, spider and bats stay pixel-identical. `index.html` places live text over the plate, with the size, spacing and position of each line tuned until it lands on the original pixels. `render.png` is the result.

The same layout is on the design board, where the text can be edited. Long text edits won't resize the boxes or buttons in the artwork.
