"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Video, Square, Loader2, X, AlertCircle, CheckCircle } from "lucide-react";

interface VideoRecorderProps {
  isOpen: boolean;
  onClose: () => void;
  onRecordingComplete: (videoBlob: Blob) => void;
  maxDuration?: number; // in seconds
  prompt?: string;
}

export function VideoRecorder({
  isOpen,
  onClose,
  onRecordingComplete,
  maxDuration = 30,
  prompt = "Could you describe what happened?",
}: VideoRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [permissionGranted, setPermissionGranted] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const previewVideoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize camera when modal opens
  useEffect(() => {
    if (isOpen) {
      initializeCamera();
    } else {
      cleanup();
    }

    return () => cleanup();
  }, [isOpen]);

  // Timer for recording duration
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setElapsedTime((prev) => {
          if (prev >= maxDuration - 1) {
            stopRecording();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording, maxDuration]);

  const initializeCamera = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true,
      });

      streamRef.current = stream;
      setPermissionGranted(true);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Camera access error:", err);
      if (err instanceof DOMException) {
        if (err.name === "NotAllowedError") {
          setError("Camera and microphone access denied. Please allow access in your browser settings.");
        } else if (err.name === "NotFoundError") {
          setError("No camera or microphone found. Please connect a device.");
        } else {
          setError(`Camera error: ${err.message}`);
        }
      } else {
        setError("Failed to access camera and microphone.");
      }
    }
  };

  const cleanup = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
    setIsPreviewing(false);
    setRecordedBlob(null);
    setElapsedTime(0);
    setPermissionGranted(false);
    chunksRef.current = [];
  };

  const startRecording = useCallback(() => {
    if (!streamRef.current) return;

    chunksRef.current = [];
    setElapsedTime(0);

    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
      ? "video/webm;codecs=vp9,opus"
      : MediaRecorder.isTypeSupported("video/webm")
      ? "video/webm"
      : "video/mp4";

    const mediaRecorder = new MediaRecorder(streamRef.current, { mimeType });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setRecordedBlob(blob);
      setIsPreviewing(true);

      // Set up preview video
      if (previewVideoRef.current) {
        previewVideoRef.current.src = URL.createObjectURL(blob);
      }
    };

    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.start(100); // Collect data every 100ms
    setIsRecording(true);
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  const retakeRecording = () => {
    if (previewVideoRef.current?.src) {
      URL.revokeObjectURL(previewVideoRef.current.src);
    }
    setRecordedBlob(null);
    setIsPreviewing(false);
    setElapsedTime(0);
  };

  const submitRecording = () => {
    if (recordedBlob) {
      onRecordingComplete(recordedBlob);
      cleanup();
      onClose();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="video-recorder-modal"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/70"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-2xl bg-background rounded-2xl shadow-xl overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Video className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-semibold">Record Video Response</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-full hover:bg-muted transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Prompt */}
            <div className="px-6 py-3 bg-muted/50 border-b">
              <p className="text-sm text-muted-foreground">Please answer the following question:</p>
              <p className="font-medium mt-1">{prompt}</p>
            </div>

            {/* Video Area */}
            <div className="relative aspect-video bg-black">
              {error ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-6">
                  <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
                  <p className="text-center text-red-200">{error}</p>
                  <button
                    onClick={initializeCamera}
                    className="mt-4 px-4 py-2 bg-primary rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              ) : isPreviewing ? (
                <video
                  ref={previewVideoRef}
                  className="w-full h-full object-cover"
                  controls
                  autoPlay
                />
              ) : (
                <>
                  <video
                    ref={videoRef}
                    className="w-full h-full object-cover mirror"
                    autoPlay
                    muted
                    playsInline
                  />
                  {/* Recording indicator */}
                  {isRecording && (
                    <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-600 text-white px-3 py-1 rounded-full text-sm">
                      <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                      REC
                    </div>
                  )}
                  {/* Timer */}
                  {(isRecording || elapsedTime > 0) && (
                    <div className="absolute top-4 right-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm font-mono">
                      {formatTime(elapsedTime)} / {formatTime(maxDuration)}
                    </div>
                  )}
                  {/* Loading state */}
                  {!permissionGranted && !error && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Loader2 className="h-8 w-8 text-white animate-spin" />
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Controls */}
            <div className="px-6 py-4 border-t flex items-center justify-between">
              {isPreviewing ? (
                <>
                  <button
                    onClick={retakeRecording}
                    className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
                  >
                    Retake
                  </button>
                  <button
                    onClick={submitRecording}
                    className="px-6 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors flex items-center gap-2"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Use This Recording
                  </button>
                </>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    Max duration: {maxDuration} seconds
                  </p>
                  {isRecording ? (
                    <button
                      onClick={stopRecording}
                      className="px-6 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors flex items-center gap-2"
                    >
                      <Square className="h-4 w-4" />
                      Stop Recording
                    </button>
                  ) : (
                    <button
                      onClick={startRecording}
                      disabled={!permissionGranted}
                      className="px-6 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                      <Video className="h-4 w-4" />
                      Start Recording
                    </button>
                  )}
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}

      <style jsx>{`
        .mirror {
          transform: scaleX(-1);
        }
      `}</style>
    </AnimatePresence>
  );
}
