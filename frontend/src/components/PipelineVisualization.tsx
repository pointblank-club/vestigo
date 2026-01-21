import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  FileCheck,
  Loader2,
  CheckCircle2,
  Clock,
  AlertCircle,
  FolderTree,
  Binary,
  HardDrive,
  Cpu,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { API_CONFIG } from "@/config/api";

interface PipelineStep {
  id: string;
  label: string;
  status: "pending" | "processing" | "complete" | "failed";
  description?: string;
}

interface BootloaderJob {
  type: string;
  file: string;
  size: number;
  reason: string;
  status: "pending" | "processing" | "complete";
  job_id?: string;
  path?: string;
}

interface BinaryJob {
  filename: string;
  path: string;
  size: number;
  directory: string;
  status: "pending" | "processing" | "complete";
  job_id?: string;
}

interface PipelineVisualizationProps {
  jobId: string;
  routingDecision: string;
  routingReason: string;
  bootloaders?: BootloaderJob[];
  binaries?: BinaryJob[];
  status?: string;
  autoRefresh?: boolean;
}

export const PipelineVisualization = ({
  jobId,
  routingDecision,
  routingReason,
  bootloaders = [],
  binaries = [],
  status = "processing",
  autoRefresh = true,
}: PipelineVisualizationProps) => {
  const [refreshedData, setRefreshedData] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const navigate = useNavigate();

  // Auto-refresh job data
  useEffect(() => {
    if (!autoRefresh || status === "complete" || status === "failed") return;

    const interval = setInterval(async () => {
      try {
        setIsRefreshing(true);
        const res = await fetch(`${API_CONFIG.BASE_URL}/job/${jobId}/complete-analysis`);
        const data = await res.json();
        setRefreshedData(data);
      } catch (err) {
        console.error("Failed to refresh job data:", err);
      } finally {
        setIsRefreshing(false);
      }
    }, 3000); // Refresh every 3 seconds

    return () => clearInterval(interval);
  }, [jobId, autoRefresh, status]);

  // Use refreshed data if available
  const currentBootloaders = refreshedData?.job_storage_data?.bootloaders || bootloaders;
  const currentBinaries = refreshedData?.job_storage_data?.feature_extraction_results?.binaries || binaries;
  const currentStatus = refreshedData?.job_storage_data?.status || status;

  const getRoutingBadgeColor = (decision: string) => {
    switch (decision) {
      case "PATH_A_BARE_METAL":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "PATH_B_LINUX_FS":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      case "PATH_C_HARD_TARGET":
        return "bg-orange-500/10 text-orange-500 border-orange-500/20";
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "complete":
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case "processing":
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case "pending":
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case "failed":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const renderPathAPipeline = () => {
    if (routingDecision !== "PATH_A_BARE_METAL") return null;

    return (
      <Card className="bg-card border-blue-500/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Binary className="w-5 h-5 text-blue-500" />
            <CardTitle className="text-xl">PATH A: Bare Metal Binary Analysis</CardTitle>
          </div>
          <CardDescription>Direct binary analysis pipeline</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3 text-sm">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-500" />
              <span className="font-medium">Feature Extraction</span>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center gap-2">
              <Binary className="w-4 h-4 text-blue-500" />
              <span className="font-medium">ML Classification</span>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-blue-500" />
              <span className="font-medium">Results</span>
            </div>
          </div>
          
          {currentBinaries && currentBinaries.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Binaries Pending Analysis ({currentBinaries.length})</p>
                <p className="text-xs text-muted-foreground italic">Click to view analysis</p>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-2">
                {currentBinaries.slice(0, 10).map((binary: any, idx: number) => (
                  <div
                    key={idx}
                    onClick={() => {
                      if (binary.job_id) {
                        navigate(`/job/${binary.job_id}/analysis`);
                      }
                    }}
                    className={`flex items-center justify-between p-2 bg-background rounded-md border border-border ${
                      binary.job_id ? 'cursor-pointer hover:bg-accent hover:border-primary/50 transition-all' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {getStatusIcon(binary.status || "pending")}
                      <span className="text-sm font-mono truncate">{binary.filename}</span>
                      <Badge variant="outline" className="text-xs">
                        {binary.directory}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {formatSize(binary.size)}
                      </span>
                      {binary.job_id && <ExternalLink className="w-3 h-3 text-muted-foreground" />}
                    </div>
                  </div>
                ))}
                {currentBinaries.length > 10 && (
                  <p className="text-xs text-muted-foreground text-center">
                    +{currentBinaries.length - 10} more binaries
                  </p>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderPathBPipeline = () => {
    if (routingDecision !== "PATH_B_LINUX_FS") return null;

    return (
      <Card className="bg-card border-green-500/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FolderTree className="w-5 h-5 text-green-500" />
            <CardTitle className="text-xl">PATH B: Linux Filesystem Analysis</CardTitle>
          </div>
          <CardDescription>Extracted filesystem scanning and analysis</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3 text-sm">
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-green-500" />
              <span className="font-medium">FS Scan</span>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center gap-2">
              <Binary className="w-4 h-4 text-green-500" />
              <span className="font-medium">Extract Binaries</span>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-green-500" />
              <span className="font-medium">Crypto Detection</span>
            </div>
          </div>

          {currentBootloaders && currentBootloaders.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Bootloaders Found ({currentBootloaders.length})</p>
                <p className="text-xs text-muted-foreground italic">Click to view analysis</p>
              </div>
              <div className="space-y-2">
                {currentBootloaders.map((bootloader: any, idx: number) => (
                  <div
                    key={idx}
                    onClick={() => {
                      if (bootloader.job_id) {
                        navigate(`/job/${bootloader.job_id}/analysis`);
                      }
                    }}
                    className={`flex items-center justify-between p-3 bg-background rounded-md border border-border ${
                      bootloader.job_id ? 'cursor-pointer hover:bg-accent hover:border-primary/50 transition-all' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3 flex-1">
                      {getStatusIcon(bootloader.status || "pending")}
                      <div className="space-y-1">
                        <p className="text-sm font-mono font-medium">{bootloader.file}</p>
                        <p className="text-xs text-muted-foreground">{bootloader.reason}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <Badge variant="outline" className="mb-1">
                          {bootloader.type}
                        </Badge>
                        <p className="text-xs text-muted-foreground">
                          {formatSize(bootloader.size)}
                        </p>
                      </div>
                      {bootloader.job_id && <ExternalLink className="w-4 h-4 text-muted-foreground" />}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {currentBinaries && currentBinaries.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">
                  Extracted Binaries ({currentBinaries.length})
                </p>
                <p className="text-xs text-muted-foreground italic">Click to view analysis</p>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-2">
                {currentBinaries.slice(0, 8).map((binary: any, idx: number) => (
                  <div
                    key={idx}
                    onClick={() => {
                      if (binary.job_id) {
                        navigate(`/job/${binary.job_id}/analysis`);
                      }
                    }}
                    className={`flex items-center justify-between p-2 bg-background rounded-md border border-border ${
                      binary.job_id ? 'cursor-pointer hover:bg-accent hover:border-primary/50 transition-all' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {getStatusIcon(binary.status || "pending")}
                      <span className="text-sm font-mono truncate">{binary.filename}</span>
                      <Badge variant="outline" className="text-xs">
                        {binary.directory}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {formatSize(binary.size)}
                      </span>
                      {binary.job_id && <ExternalLink className="w-3 h-3 text-muted-foreground" />}
                    </div>
                  </div>
                ))}
                {currentBinaries.length > 8 && (
                  <p className="text-xs text-muted-foreground text-center">
                    +{currentBinaries.length - 8} more binaries
                  </p>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      {/* Routing Decision Header */}
      <Card className="bg-card border-border">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <FileCheck className="w-6 h-6 text-primary" />
              <div>
                <h3 className="text-lg font-semibold">Analysis Route</h3>
                <p className="text-sm text-muted-foreground">Job ID: {jobId}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isRefreshing && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
              <Badge
                variant="outline"
                className={`text-lg px-4 py-1 ${getRoutingBadgeColor(routingDecision)}`}
              >
                {routingDecision}
              </Badge>
            </div>
          </div>

          <div className="bg-background p-4 rounded-md border border-border">
            <p className="text-sm">
              <span className="font-medium text-primary">Reason:</span> {routingReason}
            </p>
          </div>

          {/* Overall Status */}
          <div className="mt-4 flex items-center gap-2">
            <div className="flex items-center gap-2">
              {getStatusIcon(currentStatus)}
              <span className="text-sm font-medium capitalize">{currentStatus}</span>
            </div>
            {currentStatus === "processing" && (
              <div className="flex-1 ml-4">
                <Progress value={33} className="h-2" />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pipeline-specific visualization */}
      {renderPathAPipeline()}
      {renderPathBPipeline()}

      {/* Job Summary */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg">Pipeline Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-background rounded-md border border-border">
              <p className="text-2xl font-bold text-primary">
                {currentBootloaders.length}
              </p>
              <p className="text-xs text-muted-foreground">Bootloaders</p>
            </div>
            <div className="text-center p-3 bg-background rounded-md border border-border">
              <p className="text-2xl font-bold text-primary">
                {currentBinaries.length}
              </p>
              <p className="text-xs text-muted-foreground">Binaries</p>
            </div>
            <div className="text-center p-3 bg-background rounded-md border border-border">
              <p className="text-2xl font-bold text-primary">
                {currentBootloaders.length + currentBinaries.length}
              </p>
              <p className="text-xs text-muted-foreground">Total Jobs</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
