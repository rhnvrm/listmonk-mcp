"""Pydantic models for Listmonk MCP server data validation and serialization."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

# Enums for status fields and types


class SubscriberStatusEnum(StrEnum):
    """Subscriber status enumeration."""

    enabled = "enabled"
    disabled = "disabled"
    blocklisted = "blocklisted"


class CampaignStatusEnum(StrEnum):
    """Campaign status enumeration."""

    draft = "draft"
    scheduled = "scheduled"
    running = "running"
    paused = "paused"
    finished = "finished"
    cancelled = "cancelled"


class CampaignTypeEnum(StrEnum):
    """Campaign type enumeration."""

    regular = "regular"
    optin = "optin"


class ContentTypeEnum(StrEnum):
    """Content type enumeration."""

    richtext = "richtext"
    html = "html"
    markdown = "markdown"
    plain = "plain"
    visual = "visual"


class ListTypeEnum(StrEnum):
    """Mailing list type enumeration."""

    public = "public"
    private = "private"


class OptinTypeEnum(StrEnum):
    """Opt-in type enumeration."""

    single = "single"
    double = "double"


class TemplateTypeEnum(StrEnum):
    """Template type enumeration."""

    campaign = "campaign"
    tx = "tx"


# Base models for common patterns


class TimestampedModel(BaseModel):
    """Base model with created_at and updated_at timestamps."""

    created_at: datetime
    updated_at: datetime | None = None


class UUIDModel(BaseModel):
    """Base model with UUID field."""

    uuid: str = Field(..., description="Unique identifier")


# Core entity models


class MailingList(TimestampedModel, UUIDModel):
    """Mailing list model matching Listmonk API structure."""

    id: int = Field(..., description="Unique list ID")
    name: str = Field(..., min_length=1, max_length=200, description="List name")
    type: ListTypeEnum = Field(
        default=ListTypeEnum.public, description="List visibility type"
    )
    optin: OptinTypeEnum = Field(
        default=OptinTypeEnum.single, description="Opt-in confirmation type"
    )
    tags: list[str] = Field(default_factory=list, description="List tags")
    description: str | None = Field(
        None, max_length=1000, description="List description"
    )
    subscriber_count: int | None = Field(
        None, ge=0, description="Number of subscribers"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags are non-empty strings."""
        return [tag.strip() for tag in v if tag.strip()]


class Subscriber(TimestampedModel, UUIDModel):
    """Subscriber model matching Listmonk API structure."""

    id: int = Field(..., description="Unique subscriber ID")
    email: EmailStr = Field(..., description="Subscriber email address")
    name: str = Field(..., min_length=1, max_length=200, description="Subscriber name")
    status: SubscriberStatusEnum = Field(
        default=SubscriberStatusEnum.enabled, description="Subscriber status"
    )
    lists: list[dict[str, Any]] = Field(
        default_factory=list, description="Subscribed mailing lists"
    )
    attribs: dict[str, Any] = Field(
        default_factory=dict, description="Custom subscriber attributes"
    )

    @field_validator("attribs")
    @classmethod
    def validate_attribs(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate custom attributes."""
        if not isinstance(v, dict):
            raise ValueError("Attributes must be a dictionary")
        return v


class Campaign(TimestampedModel, UUIDModel):
    """Campaign model matching Listmonk API structure."""

    id: int = Field(..., description="Unique campaign ID")
    name: str = Field(..., min_length=1, max_length=200, description="Campaign name")
    subject: str = Field(
        ..., min_length=1, max_length=500, description="Email subject line"
    )
    from_email: EmailStr | None = Field(None, description="From email address")
    body: str | None = Field(None, description="Campaign body content")
    altbody: str | None = Field(None, description="Plain text alternative body")
    send_at: datetime | None = Field(None, description="Scheduled send time")
    status: CampaignStatusEnum = Field(
        default=CampaignStatusEnum.draft, description="Campaign status"
    )
    type: CampaignTypeEnum = Field(
        default=CampaignTypeEnum.regular, description="Campaign type"
    )
    content_type: ContentTypeEnum = Field(
        default=ContentTypeEnum.richtext, description="Content format"
    )
    tags: list[str] = Field(default_factory=list, description="Campaign tags")

    # Statistics fields
    views: int = Field(default=0, ge=0, description="Total views")
    clicks: int = Field(default=0, ge=0, description="Total clicks")
    to_send: int = Field(default=0, ge=0, description="Number of recipients to send to")
    sent: int = Field(default=0, ge=0, description="Number of emails sent")
    started_at: datetime | None = Field(None, description="Campaign start time")

    # Relationships
    lists: list[dict[str, Any]] = Field(
        default_factory=list, description="Target mailing lists"
    )
    template_id: int | None = Field(None, description="Template ID if using template")
    messenger: str | None = Field(None, description="Messenger backend")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags are non-empty strings."""
        return [tag.strip() for tag in v if tag.strip()]

    @field_validator("send_at")
    @classmethod
    def validate_send_at(cls, v: datetime | None) -> datetime | None:
        """Validate send_at is not in the past for scheduled campaigns."""
        if v and v <= datetime.now():
            # Allow past dates but note that they may cause API errors
            pass
        return v


class Template(TimestampedModel):
    """Template model matching Listmonk API structure."""

    id: int = Field(..., description="Unique template ID")
    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    subject: str | None = Field(None, description="Transactional template subject")
    body: str = Field(..., min_length=1, description="Template HTML body")
    type: TemplateTypeEnum = Field(
        default=TemplateTypeEnum.campaign, description="Template type"
    )
    is_default: bool = Field(
        default=False, description="Whether this is the default template"
    )


# Create/Update models for API operations


class CreateSubscriberModel(BaseModel):
    """Model for creating a new subscriber."""

    email: EmailStr = Field(..., description="Subscriber email address")
    name: str = Field(..., min_length=1, max_length=200, description="Subscriber name")
    status: SubscriberStatusEnum = Field(
        default=SubscriberStatusEnum.enabled, description="Initial status"
    )
    lists: list[int] = Field(
        default_factory=list, description="List IDs to subscribe to"
    )
    attribs: dict[str, Any] = Field(
        default_factory=dict, description="Custom attributes"
    )
    preconfirm_subscriptions: bool = Field(
        default=False, description="Skip confirmation for double opt-in lists"
    )

    @field_validator("lists")
    @classmethod
    def validate_lists(cls, v: list[int]) -> list[int]:
        """Validate list IDs are positive integers."""
        if not all(isinstance(list_id, int) and list_id > 0 for list_id in v):
            raise ValueError("All list IDs must be positive integers")
        return v


class UpdateSubscriberModel(BaseModel):
    """Model for updating an existing subscriber."""

    email: EmailStr | None = Field(None, description="New email address")
    name: str | None = Field(None, min_length=1, max_length=200, description="New name")
    status: SubscriberStatusEnum | None = Field(None, description="New status")
    lists: list[int] | None = Field(None, description="New list IDs")
    attribs: dict[str, Any] | None = Field(None, description="New custom attributes")

    @field_validator("lists")
    @classmethod
    def validate_lists(cls, v: list[int] | None) -> list[int] | None:
        """Validate list IDs are positive integers."""
        if v is not None and not all(
            isinstance(list_id, int) and list_id > 0 for list_id in v
        ):
            raise ValueError("All list IDs must be positive integers")
        return v


class CreateListModel(BaseModel):
    """Model for creating a new mailing list."""

    name: str = Field(..., min_length=1, max_length=200, description="List name")
    type: ListTypeEnum = Field(
        default=ListTypeEnum.public, description="List visibility type"
    )
    optin: OptinTypeEnum = Field(
        default=OptinTypeEnum.single, description="Opt-in confirmation type"
    )
    tags: list[str] = Field(default_factory=list, description="List tags")
    description: str | None = Field(
        None, max_length=1000, description="List description"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags are non-empty strings."""
        return [tag.strip() for tag in v if tag.strip()]


class UpdateListModel(BaseModel):
    """Model for updating an existing mailing list."""

    name: str | None = Field(
        None, min_length=1, max_length=200, description="New list name"
    )
    type: ListTypeEnum | None = Field(None, description="New list visibility type")
    optin: OptinTypeEnum | None = Field(
        None, description="New opt-in confirmation type"
    )
    tags: list[str] | None = Field(None, description="New list tags")
    description: str | None = Field(
        None, max_length=1000, description="New list description"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate tags are non-empty strings."""
        if v is not None:
            return [tag.strip() for tag in v if tag.strip()]
        return v


class CreateCampaignModel(BaseModel):
    """Model for creating a new campaign."""

    name: str = Field(..., min_length=1, max_length=200, description="Campaign name")
    subject: str = Field(
        ..., min_length=1, max_length=500, description="Email subject line"
    )
    lists: list[int] = Field(..., description="Target mailing list IDs", min_length=1)
    type: CampaignTypeEnum = Field(
        default=CampaignTypeEnum.regular, description="Campaign type"
    )
    content_type: ContentTypeEnum = Field(
        default=ContentTypeEnum.richtext, description="Content format"
    )
    from_email: EmailStr | None = Field(None, description="From email address")
    body: str | None = Field(None, description="Campaign body content")
    altbody: str | None = Field(None, description="Plain text alternative body")
    template_id: int | None = Field(None, description="Template ID to use")
    tags: list[str] = Field(default_factory=list, description="Campaign tags")
    send_at: datetime | None = Field(None, description="Scheduled send time")
    messenger: str | None = Field(None, description="Messenger backend")

    @field_validator("lists")
    @classmethod
    def validate_lists(cls, v: list[int]) -> list[int]:
        """Validate list IDs are positive integers."""
        if not all(isinstance(list_id, int) and list_id > 0 for list_id in v):
            raise ValueError("All list IDs must be positive integers")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags are non-empty strings."""
        return [tag.strip() for tag in v if tag.strip()]

    @model_validator(mode="after")
    def validate_content(self) -> "CreateCampaignModel":
        """Validate that either body or template_id is provided."""
        if not self.body and not self.template_id:
            raise ValueError("Either body content or template_id must be provided")
        return self


class UpdateCampaignModel(BaseModel):
    """Model for updating an existing campaign."""

    name: str | None = Field(
        None, min_length=1, max_length=200, description="New campaign name"
    )
    subject: str | None = Field(
        None, min_length=1, max_length=500, description="New email subject"
    )
    lists: list[int] | None = Field(
        None, description="New target mailing list IDs", min_length=1
    )
    from_email: EmailStr | None = Field(None, description="New from email address")
    body: str | None = Field(None, description="New campaign body content")
    altbody: str | None = Field(None, description="New plain text alternative body")
    template_id: int | None = Field(None, description="New template ID")
    tags: list[str] | None = Field(None, description="New campaign tags")
    send_at: datetime | None = Field(None, description="New scheduled send time")

    @field_validator("lists")
    @classmethod
    def validate_lists(cls, v: list[int] | None) -> list[int] | None:
        """Validate list IDs are positive integers."""
        if v is not None and not all(
            isinstance(list_id, int) and list_id > 0 for list_id in v
        ):
            raise ValueError("All list IDs must be positive integers")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate tags are non-empty strings."""
        if v is not None:
            return [tag.strip() for tag in v if tag.strip()]
        return v


class CreateTemplateModel(BaseModel):
    """Model for creating a new template."""

    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    subject: str | None = Field(None, description="Transactional template subject")
    body: str = Field(..., min_length=1, description="Template HTML body")
    type: TemplateTypeEnum = Field(
        default=TemplateTypeEnum.campaign, description="Template type"
    )
    is_default: bool = Field(
        default=False, description="Whether this is the default template"
    )


class UpdateTemplateModel(BaseModel):
    """Model for updating an existing template."""

    name: str | None = Field(
        None, min_length=1, max_length=200, description="New template name"
    )
    subject: str | None = Field(None, description="Transactional template subject")
    body: str | None = Field(None, min_length=1, description="New template HTML body")
    is_default: bool | None = Field(
        None, description="Whether this is the default template"
    )


class TransactionalEmailModel(BaseModel):
    """Model for sending transactional emails."""

    subscriber_email: EmailStr = Field(..., description="Recipient email address")
    template_id: int = Field(..., gt=0, description="Template ID to use")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Template data/variables"
    )
    content_type: ContentTypeEnum = Field(
        default=ContentTypeEnum.html, description="Content format"
    )
    from_email: EmailStr | None = Field(None, description="From email address")

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate template data."""
        if not isinstance(v, dict):
            raise ValueError("Template data must be a dictionary")
        return v


# MCP-specific models


class MCPToolResult(BaseModel):
    """Standard result format for MCP tool responses."""

    success: bool = Field(..., description="Whether the operation was successful")
    data: Any | None = Field(None, description="Result data if successful")
    error: dict[str, Any] | None = Field(
        None, description="Error details if unsuccessful"
    )
    message: str | None = Field(None, description="Human-readable message")


class MCPResourceContent(BaseModel):
    """Content model for MCP resources."""

    uri: str = Field(..., description="Resource URI")
    mimeType: str = Field(default="text/markdown", description="Content MIME type")
    text: str = Field(..., description="Resource content")


class SubscriberListResponse(BaseModel):
    """Response model for paginated subscriber lists."""

    results: list[Subscriber] = Field(..., description="List of subscribers")
    query: str = Field(default="", description="Search query used")
    total: int = Field(..., ge=0, description="Total number of subscribers")
    per_page: int = Field(..., gt=0, description="Items per page")
    page: int = Field(..., gt=0, description="Current page number")


class CampaignListResponse(BaseModel):
    """Response model for paginated campaign lists."""

    results: list[Campaign] = Field(..., description="List of campaigns")
    total: int = Field(..., ge=0, description="Total number of campaigns")
    per_page: int = Field(..., gt=0, description="Items per page")
    page: int = Field(..., gt=0, description="Current page number")


class ListListResponse(BaseModel):
    """Response model for mailing lists."""

    results: list[MailingList] = Field(..., description="List of mailing lists")


class TemplateListResponse(BaseModel):
    """Response model for templates."""

    results: list[Template] = Field(..., description="List of templates")


# Health check models


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    version: str | None = Field(None, description="Listmonk version")
    build: str | None = Field(None, description="Build information")
