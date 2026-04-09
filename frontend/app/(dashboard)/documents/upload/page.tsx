import { PageHeader } from "@/components/page-header";
import { UploadForm } from "@/components/upload-form";


export default function UploadPage() {
  return (
    <section className="page">
      <PageHeader
        eyebrow="Ingestion"
        title="Upload documents"
        description="Add policy, support, or operations files. Accepted formats: PDF, TXT, and Markdown."
      />
      <UploadForm />
    </section>
  );
}

