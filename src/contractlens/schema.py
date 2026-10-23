from enum import Enum

from pydantic import BaseModel, Field


class AgreementType(str, Enum):
    EMPLOYMENT = "employment"
    LEASE = "lease"
    LOAN_CREDIT = "loan_credit"
    SERVICES_CONSULTING = "services_consulting"
    SUPPLY_MANUFACTURING = "supply_manufacturing"
    STOCK_OPTION_EQUITY = "stock_option_equity"
    SHAREHOLDER_STANDSTILL = "shareholder_standstill"
    AMENDMENT = "amendment"
    TERMINATION = "termination"
    OTHER = "other"


class PartyRole(str, Enum):
    FIRST_PARTY = "first_party"  # e.g. employer, lessor, lender, buyer
    SECOND_PARTY = "second_party"  # e.g. employee, lessee, borrower, seller
    GUARANTOR = "guarantor"
    OTHER = "other"


class Party(BaseModel):
    name: str = Field(description="Legal name of the party as written in the contract")
    role: PartyRole = Field(description="The party's role in this agreement")


class ContractExtraction(BaseModel):
    agreement_type: AgreementType = Field(description="Best-matching category of this contract")
    parties: list[Party] = Field(
        default_factory=list,
        description="All named contracting parties with their role",
    )
    effective_date: str | None = Field(
        default=None,
        description="Effective/execution date of the agreement in ISO 8601 (YYYY-MM-DD) if determinable, else null",
    )
    governing_law: str | None = Field(
        default=None,
        description="US state or jurisdiction whose law governs the agreement, e.g. 'Delaware'",
    )
    term_description: str | None = Field(
        default=None,
        description="Short free-text description of the agreement's duration/term, e.g. '3 years from effective date'",
    )
    has_termination_clause: bool = Field(
        description="Whether the contract contains an explicit termination clause"
    )
    has_confidentiality_clause: bool = Field(
        description="Whether the contract contains a confidentiality / non-disclosure clause"
    )
    key_obligations: list[str] = Field(
        default_factory=list,
        description="2-5 short bullet points of the main obligations of the parties",
    )
