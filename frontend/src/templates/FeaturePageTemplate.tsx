import React from "react";

interface FeatureDetail {
  title: string;
  description: string;
  items?: string[];
}

interface CommandReference {
  command: string;
  description: string;
  permission: string;
}

interface FeaturePageProps {
  title: string;
  subtitle: string;
  description: string;
  featureDetails: FeatureDetail[];
  commandReferences?: CommandReference[];
}

/**
 * A reusable template for feature pages
 */
export function FeaturePage({
  title,
  subtitle,
  description,
  featureDetails,
  commandReferences,
}: FeaturePageProps) {
  return (
    <div className="py-8 px-4 max-w-6xl mx-auto">
      <h1 className="text-4xl font-bold mb-6">{title}</h1>
      
      <div className="bg-base-200 p-6 rounded-lg shadow-lg mb-8">
        <h2 className="text-2xl font-semibold mb-4">{subtitle}</h2>
        <p className="mb-4">{description}</p>
        
        <div className="divider my-8">Core Features</div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {featureDetails.map((detail, index) => (
            <FeatureSummary key={index} index={index} detail={detail} />
          ))}
        </div>
      </div>
      
      {commandReferences && commandReferences.length > 0 && (
        <CommandSection commandReferences={commandReferences} />
      )}
    </div>
  );
}

function FeatureSummary({ index, detail }: { index: number; detail: FeatureDetail }) {
  return <div key={index} className="card bg-base-100 shadow-md">
    <div className="card-body">
      <h3 className="card-title text-xl">{detail.title}</h3>
      <p>{detail.description}</p>
      {detail.items && (
        <ul className="list-disc pl-5 space-y-2">
          {detail.items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  </div>;
}

function CommandSection({ commandReferences }: { commandReferences: CommandReference[] }): React.ReactNode {
  return <div className="bg-base-200 p-6 rounded-lg shadow-lg mb-8">
    <h2 className="text-2xl font-semibold mb-4">Command Reference</h2>
    <div className="overflow-x-auto">
      <table className="table w-full">
        <thead>
          <tr>
            <th>Command</th>
            <th>Description</th>
            <th>Permission</th>
          </tr>
        </thead>
        <tbody>
          {commandReferences.map((cmd, index) => (
            <tr key={index}>
              <td><code>{cmd.command}</code></td>
              <td>{cmd.description}</td>
              <td>{cmd.permission}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>;
}

