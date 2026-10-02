import { useState } from "react";
import { createRoot } from "react-dom/client";
import { useApp } from "@modelcontextprotocol/ext-apps/react";


function CustomerApp() {
    const [customer, setCustomer] = useState(null);

    const { app, error } = useApp({
        appInfo: {
            name: "Customer App",
            version: "1.0.0",
        },

        capabilities: {},

        onAppCreated: (createdApp) => {
            createdApp.addEventListener(
                "toolresult",
                (result) => {
                    setCustomer(result.structuredContent);
                },
            );
        },
    });

    if (error) {
        return <p>Error: {error.message}</p>;
    }

    if (!app) {
        return <p>Connecting...</p>;
    }

    if (!customer) {
        return <p>Waiting for customer...</p>;
    }

    return (
        <main>
            <h1>Customer</h1>

            <dl>
                <dt>Name</dt>
                <dd>{customer.name}</dd>

                <dt>Company</dt>
                <dd>{customer.company}</dd>

                <dt>Email</dt>
                <dd>{customer.email}</dd>

                <dt>Status</dt>
                <dd>{customer.status}</dd>
            </dl>
        </main>
    );
}


createRoot(
    document.getElementById("root"),
).render(<CustomerApp />);