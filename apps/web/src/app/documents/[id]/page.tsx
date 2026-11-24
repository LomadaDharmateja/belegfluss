import { DocumentPage } from "./DocumentPage";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DocumentPage documentId={id} />;
}
