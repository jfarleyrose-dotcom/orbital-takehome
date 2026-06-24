import { useCallback, useState } from "react";
import { ChatSidebar } from "./components/ChatSidebar";
import { ChatWindow } from "./components/ChatWindow";
import { DocumentViewer, type JumpTarget } from "./components/DocumentViewer";
import { TooltipProvider } from "./components/ui/tooltip";
import { useConversations } from "./hooks/use-conversations";
import { useDocuments } from "./hooks/use-documents";
import { useMessages } from "./hooks/use-messages";

export default function App() {
	const {
		conversations,
		selectedId,
		loading: conversationsLoading,
		create,
		select,
		remove,
		refresh: refreshConversations,
	} = useConversations();

	const {
		messages,
		loading: messagesLoading,
		error: messagesError,
		streaming,
		streamingContent,
		send,
	} = useMessages(selectedId);

	const { documents, activeId, setActiveId, upload } = useDocuments(selectedId);

	const [jumpTarget, setJumpTarget] = useState<JumpTarget | null>(null);

	const handleSend = useCallback(
		async (content: string) => {
			await send(content);
			refreshConversations();
		},
		[send, refreshConversations],
	);

	const handleUpload = useCallback(
		async (files: File[]) => {
			// Upload sequentially so each document appears as it lands.
			let uploadedAny = false;
			for (const file of files) {
				const doc = await upload(file);
				if (doc) uploadedAny = true;
			}
			if (uploadedAny) {
				refreshConversations();
			}
		},
		[upload, refreshConversations],
	);

	const handleCreate = useCallback(async () => {
		await create();
	}, [create]);

	// A citation was clicked: focus its document and jump the viewer to the page.
	const handleCitation = useCallback(
		(documentId: string, page: number) => {
			setActiveId(documentId);
			setJumpTarget({ documentId, page, nonce: Date.now() });
		},
		[setActiveId],
	);

	return (
		<TooltipProvider delayDuration={200}>
			<div className="flex h-screen bg-neutral-50">
				<ChatSidebar
					conversations={conversations}
					selectedId={selectedId}
					loading={conversationsLoading}
					onSelect={select}
					onCreate={handleCreate}
					onDelete={remove}
				/>

				<ChatWindow
					messages={messages}
					loading={messagesLoading}
					error={messagesError}
					streaming={streaming}
					streamingContent={streamingContent}
					hasDocument={documents.length > 0}
					conversationId={selectedId}
					onSend={handleSend}
					onUpload={handleUpload}
					onCitation={handleCitation}
				/>

				<DocumentViewer
					documents={documents}
					activeId={activeId}
					onSelect={setActiveId}
					jumpTarget={jumpTarget}
				/>
			</div>
		</TooltipProvider>
	);
}
