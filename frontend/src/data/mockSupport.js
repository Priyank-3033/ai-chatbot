export const inboxItems = [
  {
    id: 1,
    customer: "Ava Thompson",
    channel: "Live Chat",
    status: "Open",
    priority: "High",
    preview: "I was charged twice for my annual plan.",
    waitTime: "2m",
  },
  {
    id: 2,
    customer: "Noah Patel",
    channel: "Email",
    status: "Pending",
    priority: "Medium",
    preview: "I cannot get past MFA after changing phones.",
    waitTime: "11m",
  },
  {
    id: 3,
    customer: "Mia Chen",
    channel: "WhatsApp",
    status: "VIP",
    priority: "High",
    preview: "Can I change my shipping address after checkout?",
    waitTime: "1m",
  },
];

export const customerProfiles = {
  1: {
    name: "Ava Thompson",
    initials: "AT",
    plan: "Scale Plan • Customer since 2023",
    health: "At Risk",
    mrr: "$480",
    region: "US-East",
    owner: "Nina Flores",
  },
  2: {
    name: "Noah Patel",
    initials: "NP",
    plan: "Growth Plan • Customer since 2024",
    health: "Healthy",
    mrr: "$190",
    region: "EU-West",
    owner: "Marcos Silva",
  },
  3: {
    name: "Mia Chen",
    initials: "MC",
    plan: "Enterprise • Customer since 2022",
    health: "VIP",
    mrr: "$2,200",
    region: "APAC",
    owner: "Leah Grant",
  },
};

export const conversationSeeds = {
  1: {
    messages: [
      {
        role: "assistant",
        content:
          "Thanks for reaching out. I can help with billing, order updates, account access, and troubleshooting. What would you like me to look into first?",
        timestamp: "09:41",
      },
      {
        role: "user",
        content: "I think I was charged twice for my annual plan.",
        timestamp: "09:42",
      },
      {
        role: "assistant",
        content:
          "I can check that with you. If this is an annual-plan charge, refunds are usually available within 14 days when usage stays under the fair-use threshold. I can also outline exactly what billing details to collect before escalation.",
        timestamp: "09:42",
      },
    ],
    sources: ["Refund Policy", "Billing Workflow"],
  },
  2: {
    messages: [
      {
        role: "assistant",
        content:
          "I saw your note about multi-factor authentication. Tell me what changed recently and I will help narrow this down quickly.",
        timestamp: "11:03",
      },
      {
        role: "user",
        content: "I changed phones and now my authenticator codes keep failing.",
        timestamp: "11:04",
      },
      {
        role: "assistant",
        content:
          "That usually happens after a device migration. The best next steps are to resync the authenticator app or use a backup code. If that still fails, capture the timestamp, browser, and a screenshot so the security team can review the login trail.",
        timestamp: "11:04",
      },
    ],
    sources: ["Troubleshooting Login Issues", "Security Escalation"],
  },
  3: {
    messages: [
      {
        role: "assistant",
        content:
          "Happy to help with your order. If you share where the order is in the fulfillment process, I can tell you what changes are still possible.",
        timestamp: "08:19",
      },
      {
        role: "user",
        content: "Can I update the shipping address after checkout if the order is already packed?",
        timestamp: "08:20",
      },
      {
        role: "assistant",
        content:
          "Once an order reaches the packed state, address changes are no longer guaranteed. The best path is to open a post-order support case and send the tracking link as soon as it becomes available.",
        timestamp: "08:20",
      },
    ],
    sources: ["Shipping and Orders"],
  },
};

export const knowledgeCards = [
  {
    title: "Refund Policy",
    detail: "Annual plans are refundable within 14 days when usage stays under the fair-use threshold.",
  },
  {
    title: "Account Recovery",
    detail: "If the customer lost email access, route to manual identity verification before updating ownership details.",
  },
  {
    title: "Order Changes",
    detail: "Orders can be edited only before they move into the packed state.",
  },
];

export const quickActions = [
  "How do I reset my password?",
  "What is your refund policy?",
  "Can I edit an order after packing?",
  "Why is MFA failing on my new phone?",
];

const cannedReplies = [
  {
    match: ["refund", "charged", "billing"],
    answer:
      "I can help with that. For annual plans, refunds are typically available within 14 days of the latest charge as long as usage remains below the fair-use threshold. If you want, I can also prepare the case details for a human billing specialist.",
    sources: ["Refund Policy", "Billing Workflow"],
  },
  {
    match: ["password", "login", "sign in"],
    answer:
      "The fastest path is to use the 'Forgot Password' link on the login page. Reset links expire after 30 minutes, so if the customer did not act in time they should request a fresh email. If they also lost access to the inbox, the case should move to manual identity verification.",
    sources: ["Account Access", "Identity Verification"],
  },
  {
    match: ["mfa", "authenticator", "backup code"],
    answer:
      "Multi-factor issues usually resolve after resyncing the authenticator app or using a backup code. If the customer changed devices, ask for the timestamp, browser, and a screenshot before escalation so the security team has enough detail to investigate.",
    sources: ["Troubleshooting Login Issues", "Security Escalation"],
  },
  {
    match: ["shipping", "order", "packed", "address"],
    answer:
      "Orders can be updated only before they enter the packed state. If the package is already packed, the best next step is to create a post-order support case and share the tracking link once it is available.",
    sources: ["Shipping and Orders"],
  },
];

export function generateMockReply(question) {
  const normalized = question.toLowerCase();
  const matched = cannedReplies.find((item) =>
    item.match.some((keyword) => normalized.includes(keyword))
  );

  if (matched) {
    return {
      answer: matched.answer,
      sources: matched.sources,
    };
  }

  return {
    answer:
      "I do not have a perfect policy match for that yet, but I can summarize the request, suggest next steps, and route it to a human support teammate when the issue touches billing disputes, security concerns, or ownership conflicts.",
    sources: ["Escalation Policy"],
  };
}
