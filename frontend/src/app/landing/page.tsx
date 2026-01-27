"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Heart, Activity, Brain, Shield } from "lucide-react";

const features = [
  {
    icon: Heart,
    title: "Heart Rate",
    description: "Continuous HR monitoring with Empatica wristband",
  },
  {
    icon: Activity,
    title: "EDA Analysis",
    description: "Electrodermal activity for stress detection",
  },
  {
    icon: Brain,
    title: "Emotion AI",
    description: "Multimodal emotion recognition from video",
  },
  {
    icon: Shield,
    title: "Clinical Grade",
    description: "Professional dashboard for clinicians",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header variant="landing" />

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="container mx-auto max-w-5xl text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-5xl md:text-7xl font-serif font-medium text-foreground leading-tight mb-8"
          >
            Be mindful
            <br />
            about your stress
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg text-muted-foreground max-w-2xl mx-auto mb-12"
          >
            MindVoice bridges the gap between patients and mental health
            professionals through continuous monitoring and multimodal emotion
            recognition.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex gap-4 justify-center"
          >
            <Button asChild size="lg" className="rounded-full px-8">
              <Link href="/home">Get Started</Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="lg"
              className="rounded-full px-8"
            >
              <Link href="#features">Learn More</Link>
            </Button>
          </motion.div>
        </div>
      </section>

      {/* Visual Section */}
      <section className="py-10 px-6">
        <div className="container mx-auto max-w-5xl">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="relative"
          >
            <div className="bg-sage-dark rounded-3xl aspect-video flex items-center justify-center overflow-hidden">
              <div className="text-center text-sage-light/60">
                <Activity
                  className="w-16 h-16 mx-auto mb-4"
                  strokeWidth={1}
                />
                <p className="text-sm">App Preview</p>
              </div>
            </div>
            <div className="absolute -bottom-8 left-0 right-0 h-32 bg-gradient-to-t from-sage-light to-transparent rounded-3xl -z-10" />
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-6 mt-16">
        <div className="container mx-auto max-w-5xl">
          <motion.h2
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-serif text-center mb-16"
          >
            Comprehensive wellness monitoring
          </motion.h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="text-center"
              >
                <div className="w-16 h-16 rounded-2xl bg-sage-light flex items-center justify-center mx-auto mb-4">
                  <feature.icon
                    className="w-7 h-7 text-sage"
                    strokeWidth={1.5}
                  />
                </div>
                <h3 className="font-serif text-lg mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto max-w-3xl">
          <div className="bg-sage rounded-3xl p-12 text-center text-primary-foreground">
            <h2 className="text-3xl md:text-4xl font-serif mb-4">
              Ready to start your journey?
            </h2>
            <p className="text-primary-foreground/80 mb-8">
              Connect with your mental health professional through MindVoice
            </p>
            <Button
              asChild
              variant="secondary"
              size="lg"
              className="rounded-full px-8 bg-white text-sage-dark hover:bg-sage-light"
            >
              <Link href="/dashboard">Access Dashboard</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="container mx-auto max-w-5xl flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-2xl font-serif">MindVoice</p>
          <p className="text-sm text-muted-foreground">
            Master&apos;s Project — Sorbonne University, Intelligent Systems
          </p>
        </div>
      </footer>
    </div>
  );
}
