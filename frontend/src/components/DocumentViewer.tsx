import { ChevronLeft, ChevronRight, FileText, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Document as PDFDocument, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { getDocumentUrl } from "../lib/api";
import type { Document } from "../types";
import { Button } from "./ui/button";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
	"pdfjs-dist/build/pdf.worker.min.mjs",
	import.meta.url,
).toString();

const MIN_WIDTH = 280;
const MAX_WIDTH = 700;
const DEFAULT_WIDTH = 400;

export interface JumpTarget {
	documentId: string;
	page: number;
	nonce: number;
}

interface DocumentViewerProps {
	documents: Document[];
	activeId: string | null;
	onSelect: (id: string) => void;
	jumpTarget?: JumpTarget | null;
}

export function DocumentViewer({
	documents,
	activeId,
	onSelect,
	jumpTarget,
}: DocumentViewerProps) {
	const [numPages, setNumPages] = useState<number>(0);
	const [currentPage, setCurrentPage] = useState(1);
	const [pdfLoading, setPdfLoading] = useState(true);
	const [pdfError, setPdfError] = useState<string | null>(null);
	const [width, setWidth] = useState(DEFAULT_WIDTH);
	const [dragging, setDragging] = useState(false);
	const containerRef = useRef<HTMLDivElement>(null);

	const activeDocument =
		documents.find((d) => d.id === activeId) ?? documents[0] ?? null;

	// Reset to the first page whenever the active document changes.
	// biome-ignore lint/correctness/useExhaustiveDependencies: only react to doc switches
	useEffect(() => {
		setCurrentPage(1);
		setPdfLoading(true);
		setPdfError(null);
	}, [activeDocument?.id]);

	// Jump to a specific page when a citation is clicked. Declared after the
	// reset effect so it wins when a click switches document and page together.
	useEffect(() => {
		if (!jumpTarget || !activeDocument) return;
		if (jumpTarget.documentId === activeDocument.id) {
			setCurrentPage(jumpTarget.page);
		}
	}, [jumpTarget, activeDocument]);

	const handleMouseDown = useCallback(
		(e: React.MouseEvent) => {
			e.preventDefault();
			setDragging(true);

			const startX = e.clientX;
			const startWidth = width;

			const handleMouseMove = (moveEvent: MouseEvent) => {
				const delta = startX - moveEvent.clientX;
				const newWidth = Math.min(
					MAX_WIDTH,
					Math.max(MIN_WIDTH, startWidth + delta),
				);
				setWidth(newWidth);
			};

			const handleMouseUp = () => {
				setDragging(false);
				window.removeEventListener("mousemove", handleMouseMove);
				window.removeEventListener("mouseup", handleMouseUp);
			};

			window.addEventListener("mousemove", handleMouseMove);
			window.addEventListener("mouseup", handleMouseUp);
		},
		[width],
	);

	const pdfPageWidth = width - 48; // account for px-4 padding on each side

	if (!activeDocument) {
		return (
			<div
				style={{ width }}
				className="flex h-full flex-shrink-0 flex-col items-center justify-center border-l border-neutral-200 bg-neutral-50"
			>
				<FileText className="mb-3 h-10 w-10 text-neutral-300" />
				<p className="text-sm text-neutral-400">No documents uploaded</p>
			</div>
		);
	}

	const pdfUrl = getDocumentUrl(activeDocument.id);

	return (
		<div
			ref={containerRef}
			style={{ width }}
			className="relative flex h-full flex-shrink-0 flex-col border-l border-neutral-200 bg-white"
		>
			{/* Resize handle */}
			<div
				className={`absolute top-0 left-0 z-10 h-full w-1.5 cursor-col-resize transition-colors hover:bg-neutral-300 ${
					dragging ? "bg-neutral-400" : ""
				}`}
				onMouseDown={handleMouseDown}
			/>

			{/* Document switcher — one tab per document in the conversation */}
			<div className="border-b border-neutral-100">
				<div className="flex items-center justify-between px-4 pt-3">
					<span className="text-xs font-medium uppercase tracking-wide text-neutral-400">
						{documents.length} document{documents.length !== 1 ? "s" : ""}
					</span>
				</div>
				<div className="flex flex-wrap gap-1.5 px-3 py-2.5">
					{documents.map((doc) => {
						const isActive = doc.id === activeDocument.id;
						return (
							<button
								type="button"
								key={doc.id}
								onClick={() => onSelect(doc.id)}
								title={doc.filename}
								className={`flex max-w-[180px] items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
									isActive
										? "border-neutral-300 bg-neutral-100 text-neutral-900"
										: "border-transparent text-neutral-500 hover:bg-neutral-50"
								}`}
							>
								<FileText className="h-3.5 w-3.5 flex-shrink-0" />
								<span className="truncate">{doc.filename}</span>
							</button>
						);
					})}
				</div>
			</div>

			{/* Active document title */}
			<div className="border-b border-neutral-100 px-4 py-2.5">
				<p className="truncate text-sm font-medium text-neutral-800">
					{activeDocument.filename}
				</p>
				<p className="text-xs text-neutral-400">
					{activeDocument.page_count} page
					{activeDocument.page_count !== 1 ? "s" : ""}
				</p>
			</div>

			{/* PDF content */}
			<div className="flex-1 overflow-y-auto p-4">
				{pdfError && (
					<div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
						{pdfError}
					</div>
				)}

				<PDFDocument
					key={activeDocument.id}
					file={pdfUrl}
					onLoadSuccess={({ numPages: pages }) => {
						setNumPages(pages);
						setPdfLoading(false);
						setPdfError(null);
					}}
					onLoadError={(error) => {
						setPdfError(`Failed to load PDF: ${error.message}`);
						setPdfLoading(false);
					}}
					loading={
						<div className="flex items-center justify-center py-12">
							<Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
						</div>
					}
				>
					{!pdfLoading && !pdfError && (
						<Page
							pageNumber={currentPage}
							width={pdfPageWidth}
							loading={
								<div className="flex items-center justify-center py-12">
									<Loader2 className="h-5 w-5 animate-spin text-neutral-300" />
								</div>
							}
						/>
					)}
				</PDFDocument>
			</div>

			{/* Page navigation */}
			{numPages > 0 && (
				<div className="flex items-center justify-center gap-3 border-t border-neutral-100 px-4 py-2.5">
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						disabled={currentPage <= 1}
						onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
					>
						<ChevronLeft className="h-4 w-4" />
					</Button>
					<span className="text-xs text-neutral-500">
						Page {currentPage} of {numPages}
					</span>
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						disabled={currentPage >= numPages}
						onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
					>
						<ChevronRight className="h-4 w-4" />
					</Button>
				</div>
			)}
		</div>
	);
}
