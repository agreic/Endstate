"""Neo4j container management for testing and development."""

import time
from typing import Optional

from docker.models.containers import Container
import docker
from docker.errors import NotFound as DockerNotFound, APIError as DockerAPIError

from .exceptions import ContainerError, ConnectionError


class Neo4jContainer:
    """Manages a Neo4j Docker container for testing."""
    
    def __init__(
        self,
        image: str = "neo4j:5.15",
        password: str = "testpassword",
        port: int = 7687,
        http_port: int = 7474,
        name: str = "neo4j-test"
    ) -> None:
        self.image = image
        self.password = password
        self.port = port
        self.http_port = http_port
        self.name = name
        self.container: Optional[Container] = None
        self.client = docker.from_env()
    
    def start(self) -> None:
        """Start the Neo4j container."""
        try:
            # Remove existing container with same name
            try:
                existing = self.client.containers.get(self.name)
                existing.remove(force=True)
            except DockerNotFound:
                pass
            
            # Clean up existing volumes with same name
            self._cleanup_volumes()
            
            # Start new container
            self.container = self.client.containers.run(
                self.image,
                name=self.name,
                ports={
                    f"{self.port}/tcp": None,  # Random host port
                    f"{self.http_port}/tcp": None  # Random host port
                },
                environment={
                    "NEO4J_AUTH": f"neo4j/{self.password}",
                    "NEO4J_PLUGINS": "[]",
                    "NEO4J_dbms_security_procedures_unrestricted": "apoc.*",
                    "NEO4J_dbms_memory_heap_initial__size": "512m",
                    "NEO4J_dbms_memory_heap_max__size": "1G"
                },
                volumes=[
                    f"{self.name}_data:/data",
                    f"{self.name}_logs:/logs"
                ],
                detach=True,
                remove=True
            )
            
            # Wait for container to be ready
            self._wait_for_ready()
            
        except DockerAPIError as e:
            raise ContainerError(f"Failed to start Neo4j container: {e}")
    
    def stop(self) -> None:
        """Stop and remove the Neo4j container and its volumes."""
        if self.container:
            try:
                self.container.stop()
                self.container.remove(force=True)
                
                # Remove associated volumes
                self._cleanup_volumes()
            except DockerAPIError as e:
                # Ignore conflicts during cleanup
                if "already in progress" not in str(e):
                    raise ContainerError(f"Failed to stop Neo4j container: {e}")
            finally:
                self.container = None
    
    def _cleanup_volumes(self) -> None:
        """Clean up volumes associated with this container."""
        try:
            volume_names = [f"{self.name}_data", f"{self.name}_logs"]
            for volume_name in volume_names:
                try:
                    volume = self.client.volumes.get(volume_name)
                    volume.remove(force=True)
                except Exception:
                    # Volume might not exist or already removed
                    pass
        except Exception:
            # If volume cleanup fails, don't fail the entire operation
            pass
    
    def _wait_for_ready(self, timeout: int = 60) -> None:
        """Wait for Neo4j to be ready to accept connections."""
        if not self.container:
            raise ContainerError("Container not started")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check container logs for readiness
            logs = self.container.logs().decode("utf-8")
            if "Started" in logs and "Bolt enabled" in logs:
                # Give it a bit more time to be fully ready
                time.sleep(2)
                return
            
            # Check if container is still running
            self.container.reload()
            if self.container.status != "running":
                raise ContainerError("Container stopped unexpectedly")
            
            time.sleep(1)
        
        raise ContainerError(f"Neo4j did not become ready within {timeout} seconds")
    
    def get_connection_uri(self) -> str:
        """Get the Bolt connection URI for the container."""
        if not self.container:
            raise ContainerError("Container not started")
        
        # Get the mapped port
        self.container.reload()
        port_mapping = self.container.ports.get(f"{self.port}/tcp")
        if not port_mapping:
            raise ContainerError("Port not mapped")
        
        host_port = port_mapping[0]["HostPort"]
        return f"bolt://localhost:{host_port}"
    
    def get_http_uri(self) -> str:
        """Get the HTTP connection URI for the container."""
        if not self.container:
            raise ContainerError("Container not started")
        
        # Get the mapped port
        self.container.reload()
        port_mapping = self.container.ports.get(f"{self.http_port}/tcp")
        if not port_mapping:
            raise ContainerError("HTTP port not mapped")
        
        host_port = port_mapping[0]["HostPort"]
        return f"http://localhost:{host_port}"
    
    def is_running(self) -> bool:
        """Check if the container is running."""
        if not self.container:
            return False
        
        try:
            self.container.reload()
            return self.container.status == "running"
        except DockerAPIError:
            return False
    
    def __enter__(self) -> "Neo4jContainer":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()