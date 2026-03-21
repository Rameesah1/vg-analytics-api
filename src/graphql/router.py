from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from strawberry.fastapi import GraphQLRouter
from src.graphql.resolvers import schema
from src.db.session import get_db


async def get_context(db: Session = Depends(get_db)):
    # inject the database session into GraphQL context
    return {"db": db}


graphql_app = GraphQLRouter(schema, context_getter=get_context)
router = APIRouter()
router.include_router(graphql_app, prefix="/api/graphql")