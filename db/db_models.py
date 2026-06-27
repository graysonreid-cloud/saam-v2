import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, JSON,
    ForeignKey, Float
)
from sqlalchemy.orm import relationship
from db.base import Base


# ---------------------------------------------------------
# Request (raw webhook event)
# ---------------------------------------------------------

class Request(Base):
    __tablename__ = "requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    source = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)

    jira_links = relationship("JiraLink", back_populates="request", cascade="all, delete-orphan")


# ---------------------------------------------------------
# JiraLink (SAAM request → Jira issue)
# ---------------------------------------------------------

class JiraLink(Base):
    __tablename__ = "jira_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, ForeignKey("requests.id"), nullable=False)
    issue_key = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    request = relationship("Request", back_populates="jira_links")


# ---------------------------------------------------------
# JiraUser (canonical Jira identity)
# ---------------------------------------------------------

class JiraUser(Base):
    __tablename__ = "jira_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    email = Column(String, nullable=True)

    team_member_id = Column(String, ForeignKey("team_members.id"), nullable=True)
    team_member = relationship("TeamMember")

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


# ---------------------------------------------------------
# TeamMember (canonical identity model)
# ---------------------------------------------------------

class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    display_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(String, nullable=True)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    behaviour_signals = relationship("TeamMemberInteraction", back_populates="team_member")


# ---------------------------------------------------------
# JiraIssue (persistent issue state)
# ---------------------------------------------------------

class JiraIssue(Base):
    __tablename__ = "jira_issues"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_key = Column(String, unique=True, index=True, nullable=False)

    summary = Column(String, nullable=True)
    status = Column(String, nullable=True)
    issue_type = Column(String, nullable=True)
    priority = Column(String, nullable=True)

    reporter_id = Column(String, ForeignKey("jira_users.id"), nullable=True)
    assignee_id = Column(String, ForeignKey("jira_users.id"), nullable=True)

    reporter = relationship("JiraUser", foreign_keys=[reporter_id])
    assignee = relationship("JiraUser", foreign_keys=[assignee_id])

    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    events = relationship("JiraEvent", back_populates="issue", cascade="all, delete-orphan")


# ---------------------------------------------------------
# JiraEvent (every webhook event)
# ---------------------------------------------------------

class JiraEvent(Base):
    __tablename__ = "jira_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id = Column(String, ForeignKey("jira_issues.id"), nullable=False)

    event_type = Column(String, nullable=False)
    raw_payload = Column(JSON, nullable=False)

    triggered_by_id = Column(String, ForeignKey("jira_users.id"), nullable=True)
    triggered_by = relationship("JiraUser")

    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    issue = relationship("JiraIssue", back_populates="events")


# ---------------------------------------------------------
# TeamMemberInteraction (behavioural signals)
# ---------------------------------------------------------

class TeamMemberInteraction(Base):
    __tablename__ = "team_member_interactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    team_member_id = Column(String, ForeignKey("team_members.id"), nullable=False)
    jira_event_id = Column(String, ForeignKey("jira_events.id"), nullable=False)

    signal_type = Column(String, nullable=False)
    weight = Column(Float, nullable=False)

    event_metadata = Column(JSON, nullable=True)

    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    team_member = relationship("TeamMember", back_populates="behaviour_signals")
    jira_event = relationship("JiraEvent")
