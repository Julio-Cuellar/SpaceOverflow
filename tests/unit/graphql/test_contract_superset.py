"""The real schema includes everything Dev B defined in contracts/schema.graphql."""

from __future__ import annotations

from pathlib import Path

from graphql import (
    GraphQLEnumType,
    GraphQLObjectType,
    build_ast_schema,
    parse,
)
from graphql.utilities import print_schema

from spaceapp.interfaces.graphql.schema import schema

CONTRACT = Path("contracts/schema.graphql")


def test_every_type_field_and_enum_value_of_the_frontend_contract_exists() -> None:
    wanted = build_ast_schema(parse(CONTRACT.read_text(encoding="utf-8")))
    ours = schema._schema
    for name, wanted_type in wanted.type_map.items():
        if name.startswith("__"):
            continue
        actual = ours.type_map.get(name)
        assert actual is not None, f"missing type {name}"
        if isinstance(wanted_type, GraphQLEnumType):
            assert isinstance(actual, GraphQLEnumType)
            assert set(wanted_type.values) <= set(actual.values), name
        elif isinstance(wanted_type, GraphQLObjectType):
            assert isinstance(actual, GraphQLObjectType)
            for field, wanted_field in wanted_type.fields.items():
                assert field in actual.fields, f"missing {name}.{field}"
                assert str(actual.fields[field].type) == str(wanted_field.type), f"{name}.{field}"
                assert set(wanted_field.args) <= set(actual.fields[field].args), f"{name}.{field}"


def test_the_schema_can_be_printed() -> None:
    assert "type Query" in print_schema(schema._schema)
