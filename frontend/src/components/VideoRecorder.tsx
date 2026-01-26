"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Video, Square, Loader2, X, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

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

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    
    // Clear the live video feed when stopping
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

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
  }, [isRecording, maxDuration, stopRecording]);

  // Set up preview video when blob is ready and preview element is mounted
  useEffect(() => {
    if (recordedBlob && isPreviewing && previewVideoRef.current) {
      const url = URL.createObjectURL(recordedBlob);
      previewVideoRef.current.src = url;
      previewVideoRef.current.load();
      previewVideoRef.current.play().catch((e) => {
        console.log("Autoplay prevented:", e);
      });
      return () => URL.revokeObjectURL(url);
    }
  }, [recordedBlob, isPreviewing]);

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
      // Preview video src is set via useEffect when recordedBlob changes
    };

    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.start(100); // Collect data every 100ms
    setIsRecording(true);
  }, []);

  const retakeRecording = () => {
    setRecordedBlob(null);
    setIsPreviewing(false);
    setElapsedTime(0);
    // Reinitialize the camera for the live feed
    if (videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
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
                <Video className="h-5 w-5 text-sage" />
                <h2 className="text-lg font-semibold">Record Video Response</h2>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="h-5 w-5" />
              </Button>
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
                  <Button onClick={initializeCamera} variant="default" className="mt-4">
                    Try Again
                  </Button>
                </div>
              ) : isPreviewing ? (
                <video
                  ref={previewVideoRef}
                  className="w-full h-full object-cover"
                  controls
                  playsInline
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
                  <Button variant="outline" onClick={retakeRecording}>
                    Retake
                  </Button>
                  <Button
                    onClick={submitRecording}
                    className="bg-green-600 hover:bg-green-700 text-white"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Use This Recording
                  </Button>
                </>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    Max duration: {maxDuration} seconds
                  </p>
                  {isRecording ? (
                    <Button
                      onClick={stopRecording}
                      variant="destructive"
                    >
                      <Square className="h-4 w-4" />
                      Stop Recording
                    </Button>
                  ) : (
                    <Button
                      onClick={startRecording}
                      disabled={!permissionGranted}
                      variant="sage"
                    >
                      <Video className="h-4 w-4" />
                      Start Recording
                    </Button>
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
