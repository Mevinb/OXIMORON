from sqlalchemy import select

from core.contracts.enums import ModelFormat, ModelRole
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import ModelDescriptor, ModelLocation
from core.persistence.database import DatabaseManager
from core.persistence.models import ModelEntity, ModelFileModel, ModelLocationModel


class ModelService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def list_models(
        self,
        role: ModelRole | None = None,
        format: ModelFormat | None = None,
        search: str | None = None,
    ) -> list[ModelDescriptor]:
        async with self.db.session() as session:
            stmt = select(ModelEntity).order_by(ModelEntity.name.asc())
            if role:
                stmt = stmt.where(ModelEntity.role == role.value)
            if format:
                stmt = stmt.where(ModelEntity.format == format.value)
            if search:
                stmt = stmt.where(ModelEntity.name.ilike(f"%{search}%"))

            res = await session.execute(stmt)
            entities = res.scalars().all()

            descriptors: list[ModelDescriptor] = []
            for e in entities:
                # Fetch locations
                loc_stmt = (
                    select(ModelLocationModel, ModelFileModel.byte_size)
                    .join(ModelFileModel, ModelLocationModel.model_file_id == ModelFileModel.id)
                    .where(ModelFileModel.model_id == e.id)
                )
                loc_res = await session.execute(loc_stmt)
                loc_records = loc_res.all()

                locations = [
                    ModelLocation(
                        id=loc.id,
                        root_path="",
                        display_path=loc.display_path,
                        canonical_path=loc.canonical_path,
                        byte_size=byte_size or 0,
                        mtime_ns=loc.mtime_ns,
                        available=loc.available,
                        managed=loc.managed,
                    )
                    for loc, byte_size in loc_records
                ]

                descriptors.append(
                    ModelDescriptor(
                        id=e.id,
                        name=e.name,
                        role=ModelRole(e.role),
                        format=ModelFormat(e.format),
                        architecture=e.architecture,
                        quantization=e.quantization,
                        favorite=e.favorite,
                        metadata=e.metadata_json or {},
                        locations=locations,
                        created_at=e.created_at,
                        last_used_at=e.last_used_at,
                    )
                )
            return descriptors

    async def get_model(self, model_id: str) -> ModelDescriptor:
        async with self.db.session() as session:
            stmt = select(ModelEntity).where(ModelEntity.id == model_id)
            res = await session.execute(stmt)
            e = res.scalar_one_or_none()
            if not e:
                raise OximoronException(
                    code=ErrorCode.MODEL_MISSING,
                    message=f"Model {model_id} not found in registry",
                    status_code=404,
                )

            loc_stmt = (
                select(ModelLocationModel, ModelFileModel.byte_size)
                .join(ModelFileModel, ModelLocationModel.model_file_id == ModelFileModel.id)
                .where(ModelFileModel.model_id == e.id)
            )
            loc_res = await session.execute(loc_stmt)
            loc_records = loc_res.all()

            locations = [
                ModelLocation(
                    id=loc.id,
                    root_path="",
                    display_path=loc.display_path,
                    canonical_path=loc.canonical_path,
                    byte_size=byte_size or 0,
                    mtime_ns=loc.mtime_ns,
                    available=loc.available,
                    managed=loc.managed,
                )
                for loc, byte_size in loc_records
            ]

            return ModelDescriptor(
                id=e.id,
                name=e.name,
                role=ModelRole(e.role),
                format=ModelFormat(e.format),
                architecture=e.architecture,
                quantization=e.quantization,
                favorite=e.favorite,
                metadata=e.metadata_json or {},
                locations=locations,
                created_at=e.created_at,
                last_used_at=e.last_used_at,
            )

    async def toggle_favorite(self, model_id: str) -> ModelDescriptor:
        async with self.db.session() as session:
            stmt = select(ModelEntity).where(ModelEntity.id == model_id)
            res = await session.execute(stmt)
            e = res.scalar_one_or_none()
            if not e:
                raise OximoronException(
                    code=ErrorCode.MODEL_MISSING,
                    message=f"Model {model_id} not found",
                    status_code=404,
                )
            e.favorite = not e.favorite
        return await self.get_model(model_id)
