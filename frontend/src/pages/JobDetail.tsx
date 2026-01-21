import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  FileCheck,
  AlertTriangle,
  Shield,
  Clock,
  Hash,
  FileType,
  ShieldCheck,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

import { useEffect, useState } from "react";
import { API_CONFIG } from "@/config/api";

const JobDetail = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();

  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  /** Fetch job details from backend */
  const fetchJob = async () => {
    try {
      const res = await fetch(`${API_CONFIG.BASE_URL}/jobs/${jobId}`);
      const data = await res.json();
      setJob(data);
    } catch (e) {
      console.error("Error loading job:", e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchJob();
  }, [jobId]);

  /** Colors for severity */
  const getSeverityColor = (severity: string | null) => {
    switch (severity) {
      case "critical":
        return "bg-red-500/10 text-red-500 border-red-500/20";
      case "high":
        return "bg-orange-500/10 text-orange-500 border-orange-500/20";
      case "low":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      case "safe":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  /** Download JSON report */
  const downloadReport = () => {
    const blob = new Blob([JSON.stringify(job, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `vestigo-report-${job.id}.json`;
    a.click();

    URL.revokeObjectURL(url);
  };

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center text-xl">
        Loading report…
      </div>
    );

  if (!job)
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <section className="pt-32 pb-20 text-center">
          <h1 className="text-4xl font-bold">Report Not Found</h1>
          <Button className="mt-4" onClick={() => navigate("/jobs")}>
            Back to Dashboard
          </Button>
        </section>
        <Footer />
      </div>
    );

  const threats = job.threats || [];
  const threatScore = Math.min((threats.length / 5) * 100, 100);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <section className="pt-32 pb-20 px-6">
        <div className="container mx-auto max-w-5xl">
          {/* Back Button */}
          <Button
            variant="ghost"
            onClick={() => navigate("/jobs")}
            className="mb-6 -ml-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
          </Button>

          {/* Header */}
          <div className="flex items-start justify-between flex-wrap gap-4 mb-10">
            <div>
              <h1 className="text-4xl md:text-5xl font-display font-bold">
                {job.fileName}
              </h1>
              <p className="text-muted-foreground">Job ID: {job.id}</p>
            </div>

            <Button onClick={downloadReport} className="bg-primary">
              <Download className="w-4 h-4 mr-2" /> Download Report
            </Button>
          </div>

          {/* Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            <Card className="p-6 bg-card border-border">
              <p className="text-sm text-muted-foreground mb-1">Status</p>
              <p className="text-2xl font-bold capitalize">{job.status}</p>
            </Card>

            <Card className="p-6 bg-card border-border">
              <p className="text-sm text-muted-foreground mb-1">Severity</p>
              <Badge
                variant="outline"
                className={`text-lg px-3 py-1 capitalize ${getSeverityColor(
                  job.severity
                )}`}
              >
                {job.severity}
              </Badge>
            </Card>

            <Card className="p-6 bg-card border-border">
              <p className="text-sm text-muted-foreground mb-1">
                Crypto Findings
              </p>
              <p
                className={`text-2xl font-bold ${
                  threats.length > 0 ? "text-red-500" : "text-green-500"
                }`}
              >
                {threats.length}
              </p>
            </Card>

            <Card className="p-6 bg-card border-border">
              <p className="text-sm text-muted-foreground mb-1">
                Analysis Time
              </p>
              <p className="text-2xl font-bold">{job.analysisTime}</p>
            </Card>
          </div>

          {/* File Metadata */}
          <Card className="p-6 bg-card border-border mb-10">
            <h2 className="text-2xl font-display font-bold mb-6">
              File Information
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-muted-foreground text-sm mb-1">MD5 Hash</p>
                <p className="font-mono text-sm break-all">{job.hash}</p>
              </div>

              <div>
                <p className="text-muted-foreground text-sm mb-1">File Type</p>
                <p>{job.fileType}</p>
              </div>

              <div>
                <p className="text-muted-foreground text-sm mb-1">File Size</p>
                <p>{job.fileSize}</p>
              </div>

              <div>
                <p className="text-muted-foreground text-sm mb-1">
                  Uploaded At
                </p>
                <p>{new Date(job.uploadTime).toLocaleString()}</p>
              </div>
            </div>
          </Card>

          {/* Threat Score */}
          <Card className="p-6 bg-card border-border mb-10">
            <h2 className="text-2xl font-bold mb-4">Threat Score</h2>

            <div className="w-full bg-secondary h-3 rounded-xl overflow-hidden mb-3">
              <div
                className={`h-3 ${
                  threatScore > 75
                    ? "bg-red-500"
                    : threatScore > 50
                    ? "bg-orange-500"
                    : threatScore > 25
                    ? "bg-yellow-500"
                    : "bg-green-500"
                }`}
                style={{ width: `${threatScore}%` }}
              />
            </div>

            <p className="text-muted-foreground">
              {threatScore < 25 && "Low risk — No harmful crypto detected"}
              {threatScore >= 25 &&
                threatScore < 50 &&
                "Moderate risk — Some weak crypto present"}
              {threatScore >= 50 &&
                threatScore < 75 &&
                "High risk — Strong indicators of harmful crypto"}
              {threatScore >= 75 &&
                "Critical — Severe cryptographic threats detected"}
            </p>
          </Card>

          {/* Crypto Threats */}
          <Card className="p-6 bg-card border-border">
            <h2 className="text-2xl font-bold mb-6">Cryptographic Findings</h2>

            {threats.length === 0 ? (
              <div className="text-center py-10">
                <ShieldCheck className="w-16 h-16 mx-auto text-green-500 mb-4" />
                <h3 className="text-2xl font-bold">No Crypto Threats Found</h3>
                <p className="text-muted-foreground">
                  This firmware appears clean.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {threats.map((t: any, idx: number) => (
                  <Card key={idx} className="p-4 bg-secondary/30 border-border">
                    <div className="flex items-center gap-3 mb-2">
                      <AlertTriangle className="text-red-500 w-5 h-5" />
                      <h3 className="font-bold text-lg">{t.name}</h3>

                      <Badge
                        variant="outline"
                        className={getSeverityColor(
                          t.severity.toLowerCase()
                        )}
                      >
                        {t.severity}
                      </Badge>
                    </div>

                    <p className="text-sm mb-1">
                      <span className="text-muted-foreground">Variant:</span>{" "}
                      {t.variant}
                    </p>

                    <p className="text-sm mb-3 text-muted-foreground">
                      Algorithm Type: {t.algorithm}
                    </p>

                    <p className="text-sm">{t.description}</p>
                  </Card>
                ))}
              </div>
            )}
          </Card>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default JobDetail;





















