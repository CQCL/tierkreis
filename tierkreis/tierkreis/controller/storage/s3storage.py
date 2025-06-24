from pathlib import Path
from uuid import UUID
from tierkreis.controller.storage.pathstorage import PathStorageBase

import boto3
from botocore.exceptions import ClientError


class S3Backend:
    def __init__(
        self,
        workflow_id: UUID,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        name: str | None = None,
        do_cleanup: bool = False,
    ) -> None:
        self.s3 = boto3.client(  # type: ignore
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
        self.resource = boto3.resource("s3")  # type: ignore

        bucket_name = "tierkreis-workflows"
        try:
            self.s3.head_bucket(Bucket=bucket_name)
        except ClientError:
            self.s3.create_bucket(Bucket=bucket_name)

        self.bucket = self.resource.Bucket(bucket_name)
        self.workflow_dir: Path = Path(str(workflow_id))
        self.logs_path = self.workflow_dir / "logs"
        self.name = name
        if do_cleanup:
            self._delete()

    def _read_once(self, path: Path) -> bytes:
        res = self.s3.get_object(Bucket=self.bucket.name, Key=str(path))
        return res["Body"].read()

    def _read(self, path: Path) -> bytes:
        bs = self._read_once(path)
        if not bs.decode().startswith("$ref:"):
            return bs

        return self._read_once(Path(bs.decode().split(":")[1]))

    def _write(self, path: Path, value: bytes, is_ref: bool = False) -> None:
        self.s3.put_object(
            Bucket=self.bucket.name,
            Key=str(path),
            Body=value,
            Tagging=f"IsRef={is_ref}",
        )

    def _delete(self) -> None:
        if self._exists(self.workflow_dir / "_metadata"):
            obs = self.s3.list_objects_v2(
                Bucket=self.bucket.name, Prefix=str(self.workflow_dir)
            )
            if "Contents" not in obs:
                return

            contents = [{"Key": x["Key"]} for x in obs["Contents"]]  # type: ignore
            self.s3.delete_objects(
                Bucket=self.bucket.name, Delete={"Objects": contents}  # type: ignore
            )

            # The following should work on actual S3 but does not on minio...
            # obs = self.bucket.objects.filter(Prefix=str(self.workflow_dir))
            # obs.delete()

    def _link(self, src: Path, dst: Path) -> None:
        src_res = self.s3.get_object_tagging(Bucket=self.bucket.name, Key=str(src))

        for tag in src_res["TagSet"]:
            if tag["Key"] == "IsRef§" and tag["Value"] == "True":
                src = Path(self._read_once(src).decode().split(":")[1])
                break

        self._write(dst, f"$ref:{src}".encode(), True)

    def _touch(self, path: Path, is_dir: bool = False) -> None:
        self._write(path, b"")

    def _exists(self, path: Path) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket.name, Key=str(path))
            return True
        except ClientError:
            return False


class S3Storage(S3Backend, PathStorageBase): ...
