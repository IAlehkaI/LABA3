# app/grpc/server.py
import grpc
from concurrent.futures import ThreadPoolExecutor
import logging

# Правильные импорты (после генерации в app/grpc/ + __init__.py)
from app.grpc import news_pb2
from app.grpc import news_pb2_grpc

# Твои сервисы и БД
from app.services.news_service import news_service
from app.db.session import SessionLocal
from app.schemas.news import NewsCreate, NewsUpdate

logger = logging.getLogger(__name__)


class NewsServiceServicer(news_pb2_grpc.NewsServiceServicer):
    """Реализация всех методов gRPC-сервиса"""

    def ListNews(self, request, context):
        db = SessionLocal()
        try:
            news_list = news_service.get_all(db)
            items = [
                news_pb2.News(
                    id=n.id,
                    title=n.title,
                    author=n.author,
                    content=n.content,
                    summary=n.summary,
                    image_url=n.image_url or "",
                    tags=n.tags or [],
                    created_at=n.created_at.isoformat() if n.created_at else ""
                )
                for n in news_list
            ]
            return news_pb2.NewsList(items=items)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return news_pb2.NewsList()
        finally:
            db.close()

    def GetNews(self, request, context):
        db = SessionLocal()
        try:
            news = news_service.get_by_id(db, request.id)
            if not news:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Новость не найдена")
                return news_pb2.News()
            return news_pb2.News(
                id=news.id,
                title=news.title,
                author=news.author,
                content=news.content,
                summary=news.summary,
                image_url=news.image_url or "",
                tags=news.tags or [],
                created_at=news.created_at.isoformat() if news.created_at else ""
            )
        finally:
            db.close()

    def CreateNews(self, request, context):
        db = SessionLocal()
        try:
            news_in = NewsCreate(
                title=request.title,
                author=request.author,
                content=request.content,
                summary=request.summary,
                image_url=request.image_url or None,
                tags=list(request.tags)
            )
            created = news_service.create(db, news_in)
            return news_pb2.News(
                id=created.id,
                title=created.title,
                author=created.author,
                content=created.content,
                summary=created.summary,
                image_url=created.image_url or "",
                tags=created.tags or [],
                created_at=created.created_at.isoformat()
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return news_pb2.News()
        finally:
            db.close()

    def UpdateNews(self, request, context):
        db = SessionLocal()
        try:
            news_in = NewsUpdate(
                title=request.title if request.title else None,
                author=request.author if request.author else None,
                content=request.content if request.content else None,
                summary=request.summary if request.summary else None,
                image_url=request.image_url if request.image_url else None,
                tags=list(request.tags) if request.tags else None
            )
            updated = news_service.update(db, request.id, news_in)
            if not updated:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return news_pb2.News()
            return news_pb2.News(
                id=updated.id,
                title=updated.title,
                author=updated.author,
                content=updated.content,
                summary=updated.summary,
                image_url=updated.image_url or "",
                tags=updated.tags or [],
                created_at=updated.created_at.isoformat()
            )
        finally:
            db.close()

    def DeleteNews(self, request, context):
        db = SessionLocal()
        try:
            success = news_service.delete(db, request.id)
            if not success:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return news_pb2.DeleteResponse(success=False, message="Новость не найдена")
            return news_pb2.DeleteResponse(success=True, message="Новость удалена")
        finally:
            db.close()

    def SearchNews(self, request, context):
        db = SessionLocal()
        try:
            results = news_service.search(db, request.query)
            items = [
                news_pb2.News(
                    id=n.id,
                    title=n.title,
                    author=n.author,
                    content=n.content,
                    summary=n.summary,
                    image_url=n.image_url or "",
                    tags=n.tags or [],
                    created_at=n.created_at.isoformat() if n.created_at else ""
                )
                for n in results
            ]
            return news_pb2.NewsList(items=items)
        finally:
            db.close()


def serve_grpc():
    """Запуск gRPC-сервера (вызывается из main.py в отдельном потоке)"""
    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    news_pb2_grpc.add_NewsServiceServicer_to_server(NewsServiceServicer(), server)
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
    logger.info("gRPC сервер запущен на порту 50051")
    server.start()
    server.wait_for_termination()