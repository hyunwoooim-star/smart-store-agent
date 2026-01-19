"""
헬스 체크 모듈

시스템 컴포넌트의 상태 확인 및 모니터링
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum


class HealthStatus(Enum):
    """헬스 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """컴포넌트 헬스 정보"""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    last_check: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """전체 시스템 헬스 정보"""
    status: HealthStatus
    components: Dict[str, ComponentHealth]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "uptime_seconds": self.uptime_seconds,
            "components": {
                name: {
                    "status": comp.status.value,
                    "message": comp.message,
                    "latency_ms": comp.latency_ms,
                    "last_check": comp.last_check,
                    "details": comp.details,
                }
                for name, comp in self.components.items()
            }
        }


class HealthChecker:
    """헬스 체커"""

    def __init__(self):
        self._checks: Dict[str, Callable[[], ComponentHealth]] = {}
        self._start_time = time.time()

    def register(self, name: str, check_func: Callable[[], ComponentHealth]):
        """헬스 체크 함수 등록"""
        self._checks[name] = check_func

    def unregister(self, name: str):
        """헬스 체크 함수 제거"""
        if name in self._checks:
            del self._checks[name]

    def check_component(self, name: str) -> ComponentHealth:
        """단일 컴포넌트 체크"""
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="등록되지 않은 컴포넌트"
            )

        start = time.perf_counter()
        try:
            result = self._checks[name]()
            result.latency_ms = (time.perf_counter() - start) * 1000
            result.last_check = datetime.now().isoformat()
            return result
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"체크 실패: {str(e)}",
                latency_ms=(time.perf_counter() - start) * 1000
            )

    def check_all(self) -> SystemHealth:
        """모든 컴포넌트 체크"""
        components = {}
        overall_status = HealthStatus.HEALTHY

        for name in self._checks:
            health = self.check_component(name)
            components[name] = health

            # 전체 상태 결정
            if health.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif health.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED

        return SystemHealth(
            status=overall_status,
            components=components,
            uptime_seconds=time.time() - self._start_time
        )

    def get_uptime(self) -> float:
        """업타임 반환 (초)"""
        return time.time() - self._start_time


# 기본 헬스 체크 함수들
def check_disk_space(
    path: str = ".",
    warning_threshold: float = 0.8,
    critical_threshold: float = 0.9
) -> ComponentHealth:
    """디스크 공간 체크"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        usage_ratio = used / total

        if usage_ratio >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"디스크 공간 부족: {usage_ratio*100:.1f}% 사용 중"
        elif usage_ratio >= warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"디스크 공간 경고: {usage_ratio*100:.1f}% 사용 중"
        else:
            status = HealthStatus.HEALTHY
            message = f"디스크 정상: {usage_ratio*100:.1f}% 사용 중"

        return ComponentHealth(
            name="disk",
            status=status,
            message=message,
            details={
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "usage_percent": round(usage_ratio * 100, 1),
            }
        )
    except Exception as e:
        return ComponentHealth(
            name="disk",
            status=HealthStatus.UNKNOWN,
            message=f"디스크 체크 실패: {str(e)}"
        )


def check_memory_usage(
    warning_threshold: float = 0.8,
    critical_threshold: float = 0.9
) -> ComponentHealth:
    """메모리 사용량 체크"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        usage_ratio = memory.percent / 100

        if usage_ratio >= critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"메모리 부족: {memory.percent}% 사용 중"
        elif usage_ratio >= warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"메모리 경고: {memory.percent}% 사용 중"
        else:
            status = HealthStatus.HEALTHY
            message = f"메모리 정상: {memory.percent}% 사용 중"

        return ComponentHealth(
            name="memory",
            status=status,
            message=message,
            details={
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent,
            }
        )
    except ImportError:
        return ComponentHealth(
            name="memory",
            status=HealthStatus.UNKNOWN,
            message="psutil 라이브러리 필요"
        )
    except Exception as e:
        return ComponentHealth(
            name="memory",
            status=HealthStatus.UNKNOWN,
            message=f"메모리 체크 실패: {str(e)}"
        )


def check_api_key(key_name: str, env_var: str = None) -> ComponentHealth:
    """API 키 설정 체크"""
    env_var = env_var or key_name
    value = os.environ.get(env_var, "")

    if value and len(value) > 10:
        return ComponentHealth(
            name=f"api_key_{key_name}",
            status=HealthStatus.HEALTHY,
            message=f"{key_name} 설정됨",
            details={"key_length": len(value)}
        )
    elif value:
        return ComponentHealth(
            name=f"api_key_{key_name}",
            status=HealthStatus.DEGRADED,
            message=f"{key_name} 키가 너무 짧음",
            details={"key_length": len(value)}
        )
    else:
        return ComponentHealth(
            name=f"api_key_{key_name}",
            status=HealthStatus.UNHEALTHY,
            message=f"{key_name} 설정 안됨"
        )


def create_gemini_check(api_key: str = None) -> Callable[[], ComponentHealth]:
    """Gemini API 헬스 체크 생성"""
    def check() -> ComponentHealth:
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            return ComponentHealth(
                name="gemini",
                status=HealthStatus.UNHEALTHY,
                message="API 키 설정 안됨"
            )

        # 실제 API 호출 대신 키 검증
        if len(key) > 20:
            return ComponentHealth(
                name="gemini",
                status=HealthStatus.HEALTHY,
                message="Gemini API 키 설정됨"
            )
        else:
            return ComponentHealth(
                name="gemini",
                status=HealthStatus.DEGRADED,
                message="Gemini API 키 형식 의심"
            )

    return check


def create_supabase_check(url: str = None, key: str = None) -> Callable[[], ComponentHealth]:
    """Supabase 헬스 체크 생성"""
    def check() -> ComponentHealth:
        supabase_url = url or os.environ.get("SUPABASE_URL", "")
        supabase_key = key or os.environ.get("SUPABASE_KEY", "")

        if not supabase_url or not supabase_key:
            return ComponentHealth(
                name="supabase",
                status=HealthStatus.UNHEALTHY,
                message="Supabase 설정 안됨"
            )

        if "supabase" in supabase_url.lower():
            return ComponentHealth(
                name="supabase",
                status=HealthStatus.HEALTHY,
                message="Supabase 설정됨",
                details={"url": supabase_url[:30] + "..."}
            )
        else:
            return ComponentHealth(
                name="supabase",
                status=HealthStatus.DEGRADED,
                message="Supabase URL 형식 의심"
            )

    return check


def create_file_check(filepath: str) -> Callable[[], ComponentHealth]:
    """파일 존재 체크 생성"""
    def check() -> ComponentHealth:
        if os.path.exists(filepath):
            stat = os.stat(filepath)
            return ComponentHealth(
                name=f"file_{os.path.basename(filepath)}",
                status=HealthStatus.HEALTHY,
                message=f"파일 존재: {filepath}",
                details={
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            )
        else:
            return ComponentHealth(
                name=f"file_{os.path.basename(filepath)}",
                status=HealthStatus.UNHEALTHY,
                message=f"파일 없음: {filepath}"
            )

    return check


# 전역 헬스 체커
_global_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """전역 헬스 체커 반환"""
    return _global_health_checker


def setup_default_checks():
    """기본 헬스 체크 설정"""
    checker = get_health_checker()

    # 디스크 체크
    checker.register("disk", lambda: check_disk_space("."))

    # API 키 체크
    checker.register("gemini_key", create_gemini_check())
    checker.register("supabase", create_supabase_check())

    return checker
