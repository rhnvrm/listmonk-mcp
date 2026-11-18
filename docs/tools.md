# Tools and resources

v0.2.0 registers **72 tools**, **5 resources**, and **8 resource templates**.

This reference is generated from the registered MCP schemas. Tools are available only to the extent permitted by the configured Listmonk API user. Sends, imports, settings changes, and maintenance take effect on that instance.

## Tools

### `check_listmonk_health`

Check if Listmonk server is healthy and accessible.


### `add_subscriber`


    Add a new subscriber to Listmonk.

    Args:
        email: Subscriber email address
        name: Subscriber name
        lists: List of mailing list IDs to subscribe to
        status: Subscriber status (enabled, disabled, blocklisted)
        attributes: Custom subscriber attributes
        preconfirm: Whether to preconfirm subscriptions
    

- `email`: required
- `name`: required
- `lists`: required
- `status`: optional; default `enabled`
- `attributes`: optional; default `None`
- `preconfirm`: optional; default `False`

### `update_subscriber`


    Update an existing subscriber.

    Args:
        subscriber_id: ID of the subscriber to update
        email: New email address
        name: New name
        status: New status (enabled, disabled, blocklisted)
        lists: New list of mailing list IDs
        attributes: New custom attributes
    

- `subscriber_id`: required
- `email`: optional; default `None`
- `name`: optional; default `None`
- `status`: optional; default `None`
- `lists`: optional; default `None`
- `attributes`: optional; default `None`

### `remove_subscriber`


    Remove a subscriber from Listmonk.

    Args:
        subscriber_id: ID of the subscriber to remove
    

- `subscriber_id`: required

### `change_subscriber_status`


    Change subscriber status.

    Args:
        subscriber_id: ID of the subscriber
        status: New status (enabled, disabled, blocklisted)
    

- `subscriber_id`: required
- `status`: required

### `patch_subscriber`

Partially update a subscriber. Omitted fields and list memberships are preserved.

    Supplying lists replaces memberships; [] removes all memberships.
    

- `subscriber_id`: required
- `email`: optional; default `None`
- `name`: optional; default `None`
- `status`: optional; default `None`
- `lists`: optional; default `None`
- `attributes`: optional; default `None`
- `preconfirm`: optional; default `False`

### `subscriber_send_optin`


    Send a fresh opt-in confirmation email to a subscriber.

    Args:
        subscriber_id: ID of the subscriber.
    

- `subscriber_id`: required

### `blocklist_subscriber`


    Blocklist a single subscriber (cannot be re-subscribed without manual action).

    Args:
        subscriber_id: ID of the subscriber to blocklist.
    

- `subscriber_id`: required

### `blocklist_subscribers`


    Blocklist multiple subscribers in one call.

    Args:
        subscriber_ids: List of subscriber IDs to blocklist.
    

- `subscriber_ids`: required

### `manage_subscriber_lists`


    Bulk add / remove / unsubscribe subscribers from lists.

    Args:
        subscriber_ids: Subscriber IDs to update.
        target_list_ids: Lists to operate on.
        action: One of "add", "remove", "unsubscribe".
        status: Optional subscription status (e.g. "confirmed", "unconfirmed").
    

- `subscriber_ids`: required
- `target_list_ids`: required
- `action`: required
- `status`: optional; default `None`

### `get_subscriber_activity`


    Get a subscriber's activity log (opt-ins, bounces, list changes).

    Args:
        subscriber_id: ID of the subscriber.
    

- `subscriber_id`: required

### `delete_subscribers_by_query`


    Delete subscribers matching an advanced SQL query expression.

    Args:
        query: Listmonk-style SQL query, e.g. "subscribers.status='disabled'".
        list_ids: Optional restriction to specific list IDs.
    

- `query`: required
- `list_ids`: optional; default `None`

### `blocklist_subscribers_by_query`


    Blocklist subscribers matching an advanced SQL query expression.

    Args:
        query: Listmonk-style SQL query.
        list_ids: Optional restriction to specific list IDs.
    

- `query`: required
- `list_ids`: optional; default `None`

### `manage_subscriber_lists_by_query`


    Bulk add / remove / unsubscribe subscribers matching a query.

    Args:
        query: Listmonk-style SQL query.
        target_list_ids: Lists to operate on.
        action: One of "add", "remove", "unsubscribe".
        list_ids: Optional restriction to specific source list IDs.
        status: Optional subscription status.
    

- `query`: required
- `target_list_ids`: required
- `action`: required
- `list_ids`: optional; default `None`
- `status`: optional; default `None`

### `get_subscriber_bounces`


    Get bounce records for a single subscriber.

    Args:
        subscriber_id: ID of the subscriber.
    

- `subscriber_id`: required

### `delete_subscriber_bounces`


    Delete all bounce records for a single subscriber.

    Args:
        subscriber_id: ID of the subscriber.
    

- `subscriber_id`: required

### `list_bounces`


    List bounce records with pagination and filtering.

    Args:
        page: Page number.
        per_page: Page size.
        campaign_id: Optional campaign filter.
        source: Optional source filter (e.g. "smtp", "webhook").
    

- `page`: optional; default `1`
- `per_page`: optional; default `20`
- `campaign_id`: optional; default `None`
- `source`: optional; default `None`

### `get_bounce`


    Get a single bounce record by ID.

    Args:
        bounce_id: ID of the bounce record.
    

- `bounce_id`: required

### `delete_bounce`


    Delete a single bounce record.

    Args:
        bounce_id: ID of the bounce record.
    

- `bounce_id`: required

### `delete_bounces`


    Delete selected bounce records. Set all=true explicitly to delete all.

    Args:
        bounce_ids: Specific IDs to delete.
        all: Explicitly delete every bounce; cannot be combined with IDs.
    

- `bounce_ids`: optional; default `None`
- `all`: optional; default `False`

### `blocklist_bounced_subscribers`


    Blocklist subscribers who appear in selected bounces.

    Args:
        bounce_ids: Specific bounce IDs.
        all: Explicitly target every bounce; cannot be combined with IDs.
    

- `bounce_ids`: optional; default `None`
- `all`: optional; default `False`

### `import_subscribers`


    Start a subscriber import from a CSV or .zip file.

    Args:
        file_path: Absolute path to a .csv or .zip file.
        list_ids: Lists to subscribe imported users to.
        mode: "subscribe" (default) or "blocklist".
        delim: CSV delimiter (default ",").
        overwrite: Whether to overwrite existing subscribers.
        subscription_status: "confirmed" or "unconfirmed".
    

- `file_path`: required
- `list_ids`: required
- `mode`: optional; default `subscribe`
- `delim`: optional; default `,`
- `overwrite`: optional; default `True`
- `subscription_status`: optional; default `confirmed`

### `get_import_status`

Get the status of the current/last subscriber import.


### `get_import_logs`

Get logs from the current/last subscriber import.


### `stop_import`

Stop the currently running subscriber import.


### `get_mailing_lists`


    Get a page of mailing lists with optional name search and status filtering.

    This tool defaults to 100 lists per page. The configured Listmonk server
    controls any maximum; use page to retrieve additional pages, or use query
    to search list names on the server.

    Args:
        page: Page number, starting at 1
        per_page: Number of lists per page, defaulting to 100
        query: Optional search text matched against list names
        status: Optional status filter (active or archived)
    

- `page`: optional; default `1`
- `per_page`: optional; default `100`
- `query`: optional; default `None`
- `status`: optional; default `None`

### `search_mailing_lists`


    Search mailing lists by name and return their IDs for targeting campaigns.

    Archived lists are excluded by default because Listmonk hides them from
    campaign selectors. Set include_archived to true when they are needed.

    Args:
        query: Text to search for in mailing list names
        include_archived: Include archived lists in the search results
        page: Page number, starting at 1
        per_page: Number of lists per page, defaulting to 100
    

- `query`: required
- `include_archived`: optional; default `False`
- `page`: optional; default `1`
- `per_page`: optional; default `100`

### `create_mailing_list`


    Create a new mailing list.

    Args:
        name: List name
        type: List type (public, private)
        optin: Opt-in type (single, double)
        tags: List tags
        description: List description
    

- `name`: required
- `type`: optional; default `public`
- `optin`: optional; default `single`
- `tags`: optional; default `None`
- `description`: optional; default `None`

### `update_mailing_list`


    Update an existing mailing list.

    Args:
        list_id: ID of the list to update
        name: New list name
        type: New list type (public, private)
        optin: New opt-in type (single, double)
        tags: New list tags
        description: New list description
    

- `list_id`: required
- `name`: optional; default `None`
- `type`: optional; default `None`
- `optin`: optional; default `None`
- `tags`: optional; default `None`
- `description`: optional; default `None`

### `delete_mailing_list`


    Delete a mailing list.

    Args:
        list_id: ID of the list to delete
    

- `list_id`: required

### `get_list_subscribers_tool`


    Get subscribers for a specific mailing list.

    Args:
        list_id: ID of the mailing list
        page: Page number for pagination
        per_page: Number of subscribers per page
    

- `list_id`: required
- `page`: optional; default `1`
- `per_page`: optional; default `20`

### `get_campaigns`


    Get all campaigns with optional status filter.

    Args:
        status: Filter by status (draft, running, paused, finished, cancelled)
        page: Page number for pagination
        per_page: Number of campaigns per page
    

- `status`: optional; default `None`
- `page`: optional; default `1`
- `per_page`: optional; default `20`

### `get_campaign`


    Get a specific campaign by ID including its full body content.

    Args:
        campaign_id: ID of the campaign to retrieve
    

- `campaign_id`: required

### `create_campaign`


    Create a new email campaign.

    Args:
        name: Campaign name
        subject: Email subject line
        lists: List of mailing list IDs to send to
        type: Campaign type (regular, optin)
        content_type: Content type (richtext, html, markdown, plain)
        body: Campaign content body
        template_id: Template ID to use (optional)
        tags: Campaign tags
        from_email: Sender, e.g. "Name <sender@example.com>". Defaults to the
            sender configured in Listmonk settings.
    

- `name`: required
- `subject`: required
- `lists`: required
- `type`: optional; default `regular`
- `content_type`: optional; default `richtext`
- `body`: optional; default `None`
- `template_id`: optional; default `None`
- `tags`: optional; default `None`
- `from_email`: optional; default `None`

### `update_campaign`


    Update an existing campaign.

    Args:
        campaign_id: ID of the campaign to update
        name: New campaign name
        subject: New email subject
        lists: New list of mailing list IDs
        body: New campaign content
        tags: New campaign tags
        from_email: New sender, e.g. "Name <sender@example.com>"
    

- `campaign_id`: required
- `name`: optional; default `None`
- `subject`: optional; default `None`
- `lists`: optional; default `None`
- `body`: optional; default `None`
- `tags`: optional; default `None`
- `from_email`: optional; default `None`

### `send_campaign`


    Send a campaign immediately.

    Args:
        campaign_id: ID of the campaign to send
    

- `campaign_id`: required

### `schedule_campaign`


    Schedule a campaign for future delivery.

    Args:
        campaign_id: ID of the campaign to schedule
        send_at: ISO datetime string for when to send (e.g., '2024-12-25T10:00:00Z')
    

- `campaign_id`: required
- `send_at`: required

### `test_campaign`


    Send a test of a campaign to specific email addresses without affecting list members.

    Args:
        campaign_id: ID of the campaign to test.
        subscribers: Recipient emails. IMPORTANT: each must already exist as a
            subscriber on this listmonk instance (the test handler looks them
            up by email and skips unknown addresses). Add them via
            add_subscriber first if needed.
    

- `campaign_id`: required
- `subscribers`: required

### `change_campaign_status`


    Change a campaign's status.

    Args:
        campaign_id: ID of the campaign.
        status: One of "draft", "scheduled", "running", "paused", "cancelled".
    

- `campaign_id`: required
- `status`: required

### `archive_campaign`


    Toggle whether a campaign appears on the public archive page.

    Args:
        campaign_id: ID of the campaign.
        archive: True to publish to archive, False to remove.
        archive_template_id: Template to use for the archive page (optional).
        archive_meta: Extra metadata for the archive entry (optional).
        archive_slug: URL slug for the archive page (optional).
    

- `campaign_id`: required
- `archive`: optional; default `True`
- `archive_template_id`: optional; default `None`
- `archive_meta`: optional; default `None`
- `archive_slug`: optional; default `None`

### `delete_campaign`


    Delete a campaign permanently.

    Args:
        campaign_id: ID of the campaign to delete.
    

- `campaign_id`: required

### `delete_campaigns`


    Delete multiple campaigns in one call.

    Args:
        campaign_ids: List of campaign IDs to delete.
    

- `campaign_ids`: required

### `get_running_campaign_stats`

Get live stats for currently running campaigns (sent, to_send, rate, ETA).


### `get_campaign_analytics`


    Get campaign analytics (views, clicks, links, or bounces).

    Args:
        analytics_type: One of "views", "clicks", "links", "bounces".
        campaign_ids: Campaigns to fetch analytics for.
        from_date: Required ISO date lower bound (e.g. "2026-01-01").
        to_date: Required ISO date upper bound.
    

- `analytics_type`: required
- `campaign_ids`: required
- `from_date`: required
- `to_date`: required
- `interval`: optional; default `day`
- `unique`: optional; default `False`

### `get_templates`


    Get all email templates.

    Returns a list of all templates with their IDs, names, types, and default status.
    


### `get_template`


    Get a specific template by ID including its full body content.

    Args:
        template_id: ID of the template to retrieve
    

- `template_id`: required

### `create_template`


    Create a new email template.

    Args:
        name: Template name
        body: Template HTML body content
        type: Template type (campaign, tx)
        is_default: Whether this is the default template
        subject: Required email subject for transactional (tx) templates
    

- `name`: required
- `body`: required
- `type`: optional; default `campaign`
- `is_default`: optional; default `False`
- `subject`: optional; default `None`

### `update_template`


    Update an existing email template.

    Args:
        template_id: ID of the template to update
        name: New template name
        body: New template HTML body content
        is_default: Whether this is the default template
        subject: Email subject line (required for transactional templates, carried forward from existing template if omitted)
    

- `template_id`: required
- `name`: optional; default `None`
- `body`: optional; default `None`
- `is_default`: optional; default `None`
- `subject`: optional; default `None`

### `delete_template`


    Delete an email template.

    Args:
        template_id: ID of the template to delete
    

- `template_id`: required

### `set_default_template`


    Mark a template as the default for its type.

    Args:
        template_id: ID of the template to set as default.
    

- `template_id`: required

### `preview_template_body`


    Render a preview of an unsaved template body.

    Args:
        body: Template HTML body.
        template_type: One of "campaign" (default), "campaign_visual", "tx".
    

- `body`: required
- `template_type`: optional; default `campaign`

### `get_settings`


    Get the full server settings document.

    Note: secret fields (passwords, tokens) are masked as bullets in the response.
    Do not PUT this back via update_settings — use update_setting for individual keys
    or scrub secret-looking keys first.
    


### `update_settings`


    Replace the full server settings document.

    WARNING: GET /api/settings masks secrets as bullets. PUTting that body back
    overwrites real values with literal bullets. Strip any password/token/secret
    keys from `settings` before calling this — or prefer `update_setting` for
    a single key.
    

- `settings`: required

### `update_setting`


    Update a single settings key (avoids the password-masking footgun).

    Args:
        key: Dotted setting key (e.g. "appearance.public.custom_css").
        value: New value.
    

- `key`: required
- `value`: required

### `test_smtp_settings`


    Send a test email through provided SMTP settings without persisting them.

    Args:
        settings: SMTP config with host/port/username/password/etc.
    

- `settings`: required

### `reload_app`

Trigger a hot-reload of the Listmonk app (re-reads settings).


### `get_logs`

Get recent server logs.


### `get_about_info`

Get version / build / runtime info about this Listmonk instance.


### `get_dashboard_counts`

Get dashboard counts (subscribers, lists, campaigns, etc).


### `get_dashboard_charts`

Get dashboard chart data (campaign views, link clicks over time).


### `gc_subscribers`


    Garbage collect subscribers.

    Args:
        gc_type: One of "blocklisted", "orphan".
    

- `gc_type`: required

### `gc_campaign_analytics`


    Garbage collect campaign analytics.

    Args:
        analytics_type: One of "views", "clicks", "all".
        before: Required RFC3339 timestamp; only older analytics are deleted.
    

- `analytics_type`: required
- `before`: required

### `gc_unconfirmed_subscriptions`


    Delete unconfirmed double-opt-in subscriptions older than the given timestamp.

    Args:
        before: ISO timestamp; subscriptions created before this are removed.
    

- `before`: required

### `send_transactional_email`


    Send a transactional email using a template.

    Args:
        template_id: ID of the template to use
        subscriber_email: Recipient email address
        data: Template variables/data
        content_type: Content type (html, plain)
    

- `template_id`: required
- `subscriber_email`: required
- `data`: optional; default `None`
- `content_type`: optional; default `html`

### `get_media_list`


    Get all media files from Listmonk.

    Returns a list of all uploaded media with their IDs, filenames, URLs, and metadata.
    

- `page`: optional; default `1`
- `per_page`: optional; default `20`
- `query`: optional; default `None`
- `tags`: optional; default `None`

### `upload_media_file`


    Upload a media file to Listmonk.

    Args:
        file_path: Absolute path to the image file to upload
        title: Optional title/description for the media (defaults to filename)

    Returns:
        Success message with the uploaded file's URL
    

- `file_path`: required
- `title`: optional; default `None`

### `rename_media`

Deprecated: Listmonk does not support renaming media titles.

    This compatibility tool reports an error; use update_media_tags on v7.
    

- `media_id`: required
- `new_title`: required

### `update_media_tags`

Replace tags on a media item (Listmonk v7+). Pass [] to clear tags.

- `media_id`: required
- `tags`: required

### `delete_media_file`


    Delete a media file from Listmonk.

    Args:
        media_id: ID of the media file to delete

    Returns:
        Success message
    

- `media_id`: required

### `replace_in_campaign_body`


    Search and replace text in a campaign body (simple string matching).

    This is much more token-efficient than updating the entire campaign body.

    Args:
        campaign_id: ID of the campaign to edit
        search: Text to search for (exact string match)
        replace: Text to replace it with

    Returns:
        Success message with number of replacements made

    Example:
        replace_in_campaign_body(
            campaign_id=11,
            search="</p>",
            replace="</p>
<img src='https://...' style='...'>"
        )
    

- `campaign_id`: required
- `search`: required
- `replace`: required

### `regex_replace_in_campaign_body`


    Search and replace in campaign body using regex patterns.

    More powerful than simple replace - supports capturing groups and complex patterns.

    Args:
        campaign_id: ID of the campaign to edit
        pattern: Regex pattern to search for
        replace: Replacement string (can use \1, \2 for capture groups)

    Returns:
        Success message with number of replacements made

    Example:
        regex_replace_in_campaign_body(
            campaign_id=11,
            pattern=r"(Bondeni.*?</p>)",
            replace=r"\1
<img src='https://...'>"
        )
    

- `campaign_id`: required
- `pattern`: required
- `replace`: required

### `batch_replace_in_campaign_body`


    Perform multiple search-and-replace operations in one go.

    Even more efficient - fetches campaign once, does all replacements, updates once.

    Args:
        campaign_id: ID of the campaign to edit
        replacements: List of dicts with 'search' and 'replace' keys

    Returns:
        Success message with total replacements made

    Example:
        batch_replace_in_campaign_body(
            campaign_id=11,
            replacements=[
                {"search": "Text A", "replace": "Text B"},
                {"search": "Text C", "replace": "Text D"}
            ]
        )
    

- `campaign_id`: required
- `replacements`: required

## Resources

- `listmonk://subscribers` — List all subscribers with basic information.
- `listmonk://campaigns` — List all campaigns with basic information.
- `listmonk://lists` — List all mailing lists with basic information.
- `listmonk://templates` — List all email templates.
- `listmonk://media` — List all media files with details.

## Resource templates

- `listmonk://subscriber/{subscriber_id}` — Get subscriber details by ID.
- `listmonk://subscriber/email/{email}` — Get subscriber details by email address.
- `listmonk://campaign/{campaign_id}` — Get campaign details by ID.
- `listmonk://campaign/{campaign_id}/preview` — Get campaign HTML preview.
- `listmonk://list/{list_id}` — Get mailing list details by ID.
- `listmonk://list/{list_id}/subscribers` — Get subscribers for a specific mailing list.
- `listmonk://template/{template_id}` — Get template details by ID.
- `listmonk://template/{template_id}/preview` — Get full template body content.
