import { UploadCloud } from "lucide-react";

export function UploadDropzone() {
  return (
    <button
      type="button"
      className="upload-dropzone"
      data-testid="complaint-upload-dropzone"
      aria-label="Upload complaint document"
    >
      <UploadCloud size={26} aria-hidden="true" />
      <span className="upload-dropzone__primary">Drag & drop complaint document here</span>
      <span className="upload-dropzone__secondary">or click to browse</span>
    </button>
  );
}
