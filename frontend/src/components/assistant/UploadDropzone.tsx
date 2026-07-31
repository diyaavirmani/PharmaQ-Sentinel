import { UploadCloud } from "lucide-react";
import { useRef } from "react";

interface UploadDropzoneProps {
  onUploadDocument: (file: File) => void;
  selectedFilename?: string | null;
  isDisabled?: boolean;
}

export function UploadDropzone({
  onUploadDocument,
  selectedFilename = null,
  isDisabled = false
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  function handleFile(file: File | undefined) {
    if (!file || isDisabled) {
      return;
    }
    onUploadDocument(file);
  }

  return (
    <div>
      <button
        type="button"
        className="upload-dropzone"
        data-testid="complaint-upload-dropzone"
        aria-label="Upload complaint document"
        disabled={isDisabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
        }}
        onDrop={(event) => {
          event.preventDefault();
          handleFile(event.dataTransfer.files.item(0) ?? undefined);
        }}
      >
        <UploadCloud size={26} aria-hidden="true" />
        <span className="upload-dropzone__primary">Drag & drop complaint document here</span>
        <span className="upload-dropzone__secondary">or click to browse</span>
        {selectedFilename ? (
          <span className="upload-dropzone__filename">{selectedFilename}</span>
        ) : null}
      </button>
      <input
        ref={inputRef}
        type="file"
        className="upload-dropzone__input"
        accept=".pdf,.docx,.txt,.eml,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,message/rfc822"
        onChange={(event) => {
          handleFile(event.currentTarget.files?.item(0) ?? undefined);
          event.currentTarget.value = "";
        }}
      />
    </div>
  );
}
