"""
Aegis Observability Stack - Comprehensive Monitoring & Alerting

Production-ready monitoring with metrics, logging, tracing, and alerting
for the autonomous security operations platform.
"""

import logging
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

import prometheus_client as prom
from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram
import structlog
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader

from database.db import SessionLocal
from database.models import Scan, Repo, ScanStatus

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    severity: AlertSeverity
    title: str
    description: str
    source: str
    timestamp: datetime
    tags: Dict[str, str]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    active_scans: int
    queue_size: int
    error_rate: float
    response_time: float


class ObservabilityStack:
    """Comprehensive observability stack for Aegis"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.alerts: List[Alert] = []
        self.metrics_history: List[SystemMetrics] = []
        
        # Initialize structured logging
        self._setup_structured_logging()
        
        # Initialize Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Initialize OpenTelemetry
        self._setup_opentelemetry()
        
        # Alerting configuration
        self.alert_webhooks = []
        self.alert_thresholds = self._load_alert_thresholds()
        
        logger.info("📊 Observability Stack initialized")
    
    def _setup_structured_logging(self):
        """Setup structured logging with correlation IDs"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics collection"""
        # Scan metrics
        self.scan_duration = Histogram(
            'aegis_scan_duration_seconds',
            'Time spent processing security scans',
            ['agent', 'status', 'repo'],
            registry=self.registry
        )
        
        self.scan_total = Counter(
            'aegis_scans_total',
            'Total number of scans performed',
            ['status', 'repo'],
            registry=self.registry
        )
        
        self.vulnerabilities_found = Counter(
            'aegis_vulnerabilities_found_total',
            'Total vulnerabilities discovered',
            ['severity', 'type'],
            registry=self.registry
        )
        
        self.vulnerabilities_fixed = Counter(
            'aegis_vulnerabilities_fixed_total',
            'Total vulnerabilities fixed',
            ['severity', 'type'],
            registry=self.registry
        )
        
        # Agent metrics
        self.agent_duration = Histogram(
            'aegis_agent_duration_seconds',
            'Time spent by each agent',
            ['agent_type', 'status'],
            registry=self.registry
        )
        
        self.agent_success_rate = Gauge(
            'aegis_agent_success_rate',
            'Success rate of each agent',
            ['agent_type'],
            registry=self.registry
        )
        
        # System metrics
        self.system_cpu = Gauge(
            'aegis_system_cpu_usage',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory = Gauge(
            'aegis_system_memory_usage',
            'Memory usage percentage',
            registry=self.registry
        )
        
        self.active_scans = Gauge(
            'aegis_active_scans',
            'Number of currently active scans',
            registry=self.registry
        )
        
        # Queue metrics
        self.queue_size = Gauge(
            'aegis_queue_size',
            'Size of processing queue',
            ['queue_type'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_rate = Gauge(
            'aegis_error_rate',
            'Error rate percentage',
            ['service'],
            registry=self.registry
        )
        
        # Response time metrics
        self.response_time = Histogram(
            'aegis_response_time_seconds',
            'Response time for API endpoints',
            ['endpoint', 'method'],
            registry=self.registry
        )
    
    def _setup_opentelemetry(self):
        """Setup OpenTelemetry for distributed tracing"""
        try:
            # Tracing
            trace.set_tracer_provider(TracerProvider())
            tracer = trace.get_tracer(__name__)
            
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )
            
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Metrics
            reader = PrometheusMetricReader()
            provider = MeterProvider(metric_readers=[reader])
            metrics.set_meter_provider(provider)
            
            logger.info("📊 OpenTelemetry initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")
    
    def _load_alert_thresholds(self) -> Dict[str, Dict]:
        """Load alert thresholds from configuration"""
        return {
            "scan_failure_rate": {
                "warning": 0.1,  # 10%
                "critical": 0.2   # 20%
            },
            "response_time": {
                "warning": 5.0,   # 5 seconds
                "critical": 10.0  # 10 seconds
            },
            "queue_size": {
                "warning": 50,
                "critical": 100
            },
            "error_rate": {
                "warning": 0.05,  # 5%
                "critical": 0.1   # 10%
            },
            "cpu_usage": {
                "warning": 0.7,   # 70%
                "critical": 0.9   # 90%
            },
            "memory_usage": {
                "warning": 0.8,   # 80%
                "critical": 0.95  # 95%
            }
        }
    
    async def record_scan_start(self, scan_id: int, repo_name: str, agent_type: str):
        """Record the start of a scan"""
        self.active_scans.inc()
        
        logger.info(
            "scan_started",
            scan_id=scan_id,
            repo=repo_name,
            agent=agent_type,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    async def record_scan_complete(self, scan_id: int, repo_name: str, agent_type: str, 
                                   status: str, duration: float, vulnerabilities: int = 0):
        """Record the completion of a scan"""
        self.active_scans.dec()
        self.scan_duration.labels(agent=agent_type, status=status, repo=repo_name).observe(duration)
        self.scan_total.labels(status=status, repo=repo_name).inc()
        
        if vulnerabilities > 0:
            self.vulnerabilities_found.labels(severity="unknown", type="auto").inc(vulnerabilities)
        
        logger.info(
            "scan_completed",
            scan_id=scan_id,
            repo=repo_name,
            agent=agent_type,
            status=status,
            duration=duration,
            vulnerabilities=vulnerabilities
        )
    
    async def record_vulnerability_fixed(self, vuln_type: str, severity: str, repo_name: str):
        """Record a vulnerability fix"""
        self.vulnerabilities_fixed.labels(severity=severity, type=vuln_type).inc()
        
        logger.info(
            "vulnerability_fixed",
            type=vuln_type,
            severity=severity,
            repo=repo_name,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    async def record_agent_performance(self, agent_type: str, duration: float, 
                                       success: bool, error_type: str = None):
        """Record agent performance metrics"""
        self.agent_duration.labels(agent_type=agent_type, status="success" if success else "error").observe(duration)
        
        # Update success rate (this would need to be calculated properly)
        # For now, just log the event
        logger.info(
            "agent_performance",
            agent=agent_type,
            duration=duration,
            success=success,
            error_type=error_type
        )
    
    async def record_api_request(self, endpoint: str, method: str, status_code: int, 
                                 duration: float):
        """Record API request metrics"""
        self.response_time.labels(endpoint=endpoint, method=method).observe(duration)
        
        # Track error rate
        if status_code >= 400:
            error_count = 1
        else:
            error_count = 0
        
        logger.info(
            "api_request",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration=duration,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    async def collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.used / disk.total
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv
            }
            
            # Queue size (placeholder - would need actual queue implementation)
            queue_size = 0  # This would be actual queue size
            
            # Error rate (placeholder - would need actual error tracking)
            error_rate = 0.0  # This would be actual error rate
            
            # Response time (placeholder - would need actual response time tracking)
            response_time = 0.0  # This would be actual response time
            
            metrics = SystemMetrics(
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                disk_usage=disk_usage,
                network_io=network_io,
                active_scans=int(self.active_scans._value.get()),
                queue_size=queue_size,
                error_rate=error_rate,
                response_time=response_time
            )
            
            self.metrics_history.append(metrics)
            
            # Keep only last 1000 entries
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            # Check for alerts
            await self._check_threshold_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    async def _check_threshold_alerts(self, metrics: SystemMetrics):
        """Check metrics against thresholds and create alerts"""
        alerts_to_create = []
        
        # CPU usage
        if metrics.cpu_usage > self.alert_thresholds["cpu_usage"]["critical"]:
            alerts_to_create.append(Alert(
                id=f"cpu_critical_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                title="Critical CPU Usage",
                description=f"CPU usage is {metrics.cpu_usage:.1f}%",
                source="system",
                timestamp=datetime.now(timezone.utc),
                tags={"metric": "cpu", "value": str(metrics.cpu_usage)}
            ))
        elif metrics.cpu_usage > self.alert_thresholds["cpu_usage"]["warning"]:
            alerts_to_create.append(Alert(
                id=f"cpu_warning_{int(time.time())}",
                severity=AlertSeverity.HIGH,
                title="High CPU Usage",
                description=f"CPU usage is {metrics.cpu_usage:.1f}%",
                source="system",
                timestamp=datetime.now(timezone.utc),
                tags={"metric": "cpu", "value": str(metrics.cpu_usage)}
            ))
        
        # Memory usage
        if metrics.memory_usage > self.alert_thresholds["memory_usage"]["critical"]:
            alerts_to_create.append(Alert(
                id=f"memory_critical_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                title="Critical Memory Usage",
                description=f"Memory usage is {metrics.memory_usage:.1f}%",
                source="system",
                timestamp=datetime.now(timezone.utc),
                tags={"metric": "memory", "value": str(metrics.memory_usage)}
            ))
        elif metrics.memory_usage > self.alert_thresholds["memory_usage"]["warning"]:
            alerts_to_create.append(Alert(
                id=f"memory_warning_{int(time.time())}",
                severity=AlertSeverity.HIGH,
                title="High Memory Usage",
                description=f"Memory usage is {metrics.memory_usage:.1f}%",
                source="system",
                timestamp=datetime.now(timezone.utc),
                tags={"metric": "memory", "value": str(metrics.memory_usage)}
            ))
        
        # Create alerts
        for alert in alerts_to_create:
            await self.create_alert(alert)
    
    async def create_alert(self, alert: Alert):
        """Create and handle an alert"""
        self.alerts.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        # Log the alert
        logger.warning(
            "alert_created",
            alert_id=alert.id,
            severity=alert.severity.value,
            title=alert.title,
            description=alert.description,
            source=alert.source,
            tags=alert.tags
        )
        
        # Send to alert webhooks
        await self._send_alert_webhooks(alert)
    
    async def _send_alert_webhooks(self, alert: Alert):
        """Send alert to configured webhooks"""
        for webhook_url in self.alert_webhooks:
            try:
                import aiohttp
                
                payload = {
                    "alert_id": alert.id,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "tags": alert.tags
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=payload) as response:
                        if response.status != 200:
                            logger.error(f"Failed to send alert to webhook: {response.status}")
                        
            except Exception as e:
                logger.error(f"Failed to send alert webhook: {e}")
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                
                logger.info(
                    "alert_resolved",
                    alert_id=alert_id,
                    resolved_at=alert.resolved_at.isoformat()
                )
                break
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active (unresolved) alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        if severity:
            active_alerts = [alert for alert in active_alerts if alert.severity == severity]
        
        return active_alerts
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics"""
        if not self.metrics_history:
            return {}
        
        latest = self.metrics_history[-1]
        
        return {
            "system": {
                "cpu_usage": latest.cpu_usage,
                "memory_usage": latest.memory_usage,
                "disk_usage": latest.disk_usage,
                "active_scans": latest.active_scans,
                "queue_size": latest.queue_size,
                "error_rate": latest.error_rate,
                "response_time": latest.response_time
            },
            "alerts": {
                "total": len(self.alerts),
                "active": len(self.get_active_alerts()),
                "critical": len(self.get_active_alerts(AlertSeverity.CRITICAL)),
                "high": len(self.get_active_alerts(AlertSeverity.HIGH)),
                "medium": len(self.get_active_alerts(AlertSeverity.MEDIUM)),
                "low": len(self.get_active_alerts(AlertSeverity.LOW))
            },
            "prometheus_metrics": {
                "scan_duration": self.scan_duration._value._value,
                "scan_total": self.scan_total._value._value,
                "vulnerabilities_found": self.vulnerabilities_found._value._value,
                "vulnerabilities_fixed": self.vulnerabilities_fixed._value._value
            }
        }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        return prom.generate_latest(self.registry)
    
    async def start_monitoring_loop(self):
        """Start the monitoring loop"""
        while True:
            try:
                await self.collect_system_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error


# Global observability stack instance
observability_stack = ObservabilityStack()


# Decorators for automatic instrumentation
def monitor_performance(operation_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                await observability_stack.record_agent_performance(
                    agent_type=operation_name,
                    duration=duration,
                    success=True
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                await observability_stack.record_agent_performance(
                    agent_type=operation_name,
                    duration=duration,
                    success=False,
                    error_type=type(e).__name__
                )
                
                raise
        return wrapper
    return decorator


def trace_operation(operation_name: str):
    """Decorator to add distributed tracing"""
    def decorator(func):
        tracer = trace.get_tracer(__name__)
        
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(operation_name) as span:
                span.set_attribute("operation.name", operation_name)
                span.set_attribute("operation.start_time", datetime.now(timezone.utc).isoformat())
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("operation.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("operation.success", False)
                    span.set_attribute("operation.error", str(e))
                    raise
        return wrapper
    return decorator
