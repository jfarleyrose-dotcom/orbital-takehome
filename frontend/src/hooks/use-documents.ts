import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import type { Document } from "../types";

export function useDocuments(conversationId: string | null) {
	const [documents, setDocuments] = useState<Document[]>([]);
	const [activeId, setActiveId] = useState<string | null>(null);
	const [uploading, setUploading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const refresh = useCallback(async () => {
		if (!conversationId) {
			setDocuments([]);
			setActiveId(null);
			return;
		}
		try {
			setError(null);
			const detail = await api.fetchConversation(conversationId);
			const docs = detail.documents ?? [];
			setDocuments(docs);
			// Keep the current selection if it still exists; otherwise show the first.
			setActiveId((prev) =>
				prev && docs.some((d) => d.id === prev) ? prev : (docs[0]?.id ?? null),
			);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load documents");
		}
	}, [conversationId]);

	useEffect(() => {
		refresh();
	}, [refresh]);

	const upload = useCallback(
		async (file: File) => {
			if (!conversationId) return null;
			try {
				setUploading(true);
				setError(null);
				const doc = await api.uploadDocument(conversationId, file);
				// Append and focus the newly uploaded document.
				setDocuments((prev) => [...prev, doc]);
				setActiveId(doc.id);
				return doc;
			} catch (err) {
				setError(
					err instanceof Error ? err.message : "Failed to upload document",
				);
				return null;
			} finally {
				setUploading(false);
			}
		},
		[conversationId],
	);

	const activeDocument =
		documents.find((d) => d.id === activeId) ?? documents[0] ?? null;

	return {
		documents,
		activeDocument,
		activeId: activeDocument?.id ?? null,
		setActiveId,
		uploading,
		error,
		upload,
		refresh,
	};
}
