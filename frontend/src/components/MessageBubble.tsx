import { motion } from "framer-motion";
import { AlertTriangle, Bot, FileText, ShieldCheck } from "lucide-react";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import type { Citation, Message } from "../types";

interface MessageBubbleProps {
	message: Message;
	onCitation: (documentId: string, page: number) => void;
}

const CONFIDENCE_LABEL: Record<string, string> = {
	high: "High confidence",
	medium: "Medium confidence",
	low: "Low confidence",
};

function GroundingBanner({ message }: { message: Message }) {
	// Ungrounded answers are the dangerous case — flag them loudly.
	if (message.grounded === false) {
		return (
			<div className="mt-2 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
				<AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
				<span>
					This answer isn't supported by the uploaded documents. Verify it
					independently before relying on it.
				</span>
			</div>
		);
	}
	if (message.confidence === "low") {
		return (
			<div className="mt-2 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
				<AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
				<span>
					Low confidence — the documents only partially address this. Check the
					citations below.
				</span>
			</div>
		);
	}
	return null;
}

function CitationChip({
	citation,
	onCitation,
}: {
	citation: Citation;
	onCitation: (documentId: string, page: number) => void;
}) {
	const canJump =
		citation.verified && citation.document_id != null && citation.page != null;

	const pageLabel = citation.page != null ? `p.${citation.page}` : null;
	const docShort = citation.document_name.replace(/\.pdf$/i, "");

	if (!citation.verified) {
		// The quote could not be found in any document — surface it as unverified.
		return (
			<span
				title={`Couldn't verify this quote in the documents:\n"${citation.quote}"`}
				className="inline-flex items-center gap-1.5 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-600"
			>
				<AlertTriangle className="h-3 w-3 flex-shrink-0" />
				<span className="max-w-[160px] truncate">
					{citation.label || docShort} · unverified
				</span>
			</span>
		);
	}

	return (
		<button
			type="button"
			disabled={!canJump}
			onClick={() =>
				canJump &&
				onCitation(citation.document_id as string, citation.page as number)
			}
			title={`"${citation.quote}"\n— ${citation.document_name}${
				pageLabel ? `, ${pageLabel}` : ""
			}`}
			className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-600 transition-colors hover:border-neutral-300 hover:bg-neutral-50 disabled:cursor-default"
		>
			<FileText className="h-3 w-3 flex-shrink-0 text-neutral-400" />
			<span className="max-w-[200px] truncate">
				{citation.label || docShort}
			</span>
			{pageLabel && (
				<span className="font-medium text-neutral-500">{pageLabel}</span>
			)}
		</button>
	);
}

function Citations({
	message,
	onCitation,
}: {
	message: Message;
	onCitation: (documentId: string, page: number) => void;
}) {
	const citations = message.citations ?? [];
	if (citations.length === 0) return null;

	const verified = citations.filter((c) => c.verified).length;

	return (
		<div className="mt-2.5">
			<div className="mb-1.5 flex items-center gap-1.5 text-xs text-neutral-400">
				{verified > 0 && (
					<ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
				)}
				<span>
					{verified} verified source{verified !== 1 ? "s" : ""}
					{message.confidence
						? ` · ${CONFIDENCE_LABEL[message.confidence] ?? message.confidence}`
						: ""}
				</span>
			</div>
			<div className="flex flex-wrap gap-1.5">
				{citations.map((c, i) => (
					<CitationChip
						key={`${c.document_id ?? "none"}-${c.page ?? "x"}-${i}`}
						citation={c}
						onCitation={onCitation}
					/>
				))}
			</div>
		</div>
	);
}

export function MessageBubble({ message, onCitation }: MessageBubbleProps) {
	if (message.role === "system") {
		return (
			<motion.div
				initial={{ opacity: 0 }}
				animate={{ opacity: 1 }}
				transition={{ duration: 0.2 }}
				className="flex justify-center py-2"
			>
				<p className="text-xs text-neutral-400">{message.content}</p>
			</motion.div>
		);
	}

	if (message.role === "user") {
		return (
			<motion.div
				initial={{ opacity: 0, y: 8 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.2 }}
				className="flex justify-end py-1.5"
			>
				<div className="max-w-[75%] rounded-2xl rounded-br-md bg-neutral-100 px-4 py-2.5">
					<p className="whitespace-pre-wrap text-sm text-neutral-800">
						{message.content}
					</p>
				</div>
			</motion.div>
		);
	}

	// Assistant message
	return (
		<motion.div
			initial={{ opacity: 0, y: 8 }}
			animate={{ opacity: 1, y: 0 }}
			transition={{ duration: 0.2 }}
			className="flex gap-3 py-1.5"
		>
			<div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-neutral-900">
				<Bot className="h-4 w-4 text-white" />
			</div>
			<div className="min-w-0 max-w-[80%]">
				<div className="prose">
					<Streamdown>{message.content}</Streamdown>
				</div>
				<GroundingBanner message={message} />
				<Citations message={message} onCitation={onCitation} />
			</div>
		</motion.div>
	);
}

interface StreamingBubbleProps {
	content: string;
}

export function StreamingBubble({ content }: StreamingBubbleProps) {
	return (
		<div className="flex gap-3 py-1.5">
			<div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-neutral-900">
				<Bot className="h-4 w-4 text-white" />
			</div>
			<div className="min-w-0 max-w-[80%]">
				{content ? (
					<div className="prose">
						<Streamdown mode="streaming">{content}</Streamdown>
					</div>
				) : (
					<div className="flex items-center gap-1 py-2">
						<span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400" />
						<span
							className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400"
							style={{ animationDelay: "0.15s" }}
						/>
						<span
							className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400"
							style={{ animationDelay: "0.3s" }}
						/>
					</div>
				)}
				<span className="inline-block h-4 w-0.5 animate-pulse bg-neutral-400" />
			</div>
		</div>
	);
}
