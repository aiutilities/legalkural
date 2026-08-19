# WordPress.com Implementation and Rollback Plan

## Status

`OFFLINE PLAN — NO LIVE MUTATION AUTHORIZED`

## Pre-Mutation Evidence

1. Verify protected Git checkpoint and Founder-approved B7 package.
2. Export the WordPress.com site and record export checksum.
3. GET and store redacted JSON for settings, theme, pages, posts, menus,
   templates and styles.
4. Record IDs: About page `1`, Hello World post `3`, certified post `10`.
5. Capture anonymous Coming Soon screenshots and response hashes.
6. Record active Assembler theme/version and Global Styles ID.
7. Prepare an operation ledger with one reversible action per checkpoint.

## Proposed Mutation Sequence

Every step requires the later live-mutation authorization. Coming Soon remains
active throughout.

1. Upload approved logo and site-icon assets; do not activate yet.
2. Apply approved Assembler Global Styles tokens.
3. Replace default About page `1` with approved About copy, retaining revision
   history and recording before/after hashes.
4. Create Home, Judgments, Journal, Methodology, Privacy and Disclaimer as
   drafts.
5. Create the primary menu and footer navigation.
6. Configure header and footer templates.
7. Configure static Home and posts/index behaviour.
8. Publish approved structural pages while Coming Soon remains active.
9. Move Hello World post `3` to draft; do not delete it.
10. Add only approved presentation/disclaimer elements around certified post
    `10`; its certified title, slug, legal content and publication identity must
    remain unchanged.
11. Apply logo/site icon and validate every internal link.
12. Run authenticated preview validation and anonymous Coming Soon verification.

## Rollback

Rollback must execute in reverse order:

1. Restore prior logo/site icon and Global Styles.
2. Restore header/footer templates and menu assignments.
3. Restore homepage/posts settings.
4. Revert page revisions or move newly created pages to draft.
5. Restore post `3` to its prior status if changed.
6. Verify post `10` matches its pre-mutation hashes.
7. If granular rollback fails, restore from the pre-mutation export using the
   separately tested restore procedure.
8. Confirm Coming Soon remains active and `robots.txt` still blocks indexing.

## Stop Conditions

Stop immediately if credentials leak, IDs differ, post `10` changes
unexpectedly, export/rollback evidence is missing, plan limitations prevent a
safe action, accessibility cannot be retained, or Coming Soon/indexing changes
without the final B11 gate.
